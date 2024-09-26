"""Library for interacting with DJI Ryze Tello drones.
"""

# coding=utf-8
import logging
import socket
import time
from datetime import datetime
from collections import deque
from threading import Thread, Lock
from typing import Optional, Union, Type, Dict

from .enforce_types import enforce_types

import av
import numpy as np


threads_initialized = False
drones: Optional[dict] = {}
client_socket: socket.socket


class TelloException(Exception):
    pass


@enforce_types
class Tello:
    """Python wrapper to interact with the Ryze Tello drone using the official Tello api.
    Tello API documentation:
    [1.3](https://dl-cdn.ryzerobotics.com/downloads/tello/20180910/Tello%20SDK%20Documentation%20EN_1.3.pdf),
    [2.0 with EDU-only commands](https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf)
    """
    # Send and receive commands, client socket
    RESPONSE_TIMEOUT = 7  # in seconds
    TAKEOFF_TIMEOUT = 20  # in seconds
    FRAME_GRAB_TIMEOUT = 5
    TIME_BTW_COMMANDS = 0.1  # in seconds
    TIME_BTW_RC_CONTROL_COMMANDS = 0.001  # in seconds
    RETRY_COUNT = 3  # number of retries after a failed command
    TELLO_IP = '192.168.10.1'  # Tello IP address

    # Video stream, server socket
    VS_UDP_IP = '0.0.0.0'
    DEFAULT_VS_UDP_PORT = 11111
    VS_UDP_PORT = DEFAULT_VS_UDP_PORT

    CONTROL_UDP_PORT = 8889
    STATE_UDP_PORT = 8890

    # Constants for video settings
    BITRATE_AUTO = 0
    BITRATE_1MBPS = 1
    BITRATE_2MBPS = 2
    BITRATE_3MBPS = 3
    BITRATE_4MBPS = 4
    BITRATE_5MBPS = 5
    RESOLUTION_480P = 'low'
    RESOLUTION_720P = 'high'
    FPS_5 = 'low'
    FPS_15 = 'middle'
    FPS_30 = 'high'
    CAMERA_FORWARD = 0
    CAMERA_DOWNWARD = 1

    # Set up logger
    HANDLER = logging.StreamHandler()
    FORMATTER = logging.Formatter('[%(levelname)s] %(filename)s - %(lineno)d - %(message)s')
    HANDLER.setFormatter(FORMATTER)

    LOGGER = logging.getLogger('djitellopy')
    LOGGER.addHandler(HANDLER)
    LOGGER.setLevel(logging.INFO)
    # Use Tello.LOGGER.setLevel(logging.<LEVEL>) in YOUR CODE
    # to only receive logs of the desired level and higher

    # Conversion functions for state protocol fields
    INT_STATE_FIELDS = (
        # Tello EDU with mission pads enabled only
        'mid', 'x', 'y', 'z',
        # 'mpry': (custom format 'x,y,z')
        # Common entries
        'pitch', 'roll', 'yaw',
        'vgx', 'vgy', 'vgz',
        'templ', 'temph',
        'tof', 'h', 'bat', 'time'
    )
    FLOAT_STATE_FIELDS = ('baro', 'agx', 'agy', 'agz')

    state_field_converters: Dict[str, Union[Type[int], Type[float]]]
    state_field_converters = {key : int for key in INT_STATE_FIELDS}
    state_field_converters.update({key : float for key in FLOAT_STATE_FIELDS})

    # VideoCapture object
    background_frame_read: Optional['BackgroundFrameRead'] = None

    stream_on = False
    is_flying = False

    def __init__(self,
                 host=TELLO_IP,
                 retry_count=RETRY_COUNT,
                 vs_udp=VS_UDP_PORT):

        global threads_initialized, client_socket, drones

        self.address = (host, Tello.CONTROL_UDP_PORT)
        self.stream_on = False
        self.retry_count = retry_count
        self.last_received_command_timestamp = time.time()
        self.last_rc_control_timestamp = time.time()

        if not threads_initialized:
            # Run Tello command responses UDP receiver on background
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.bind(("", Tello.CONTROL_UDP_PORT))
            response_receiver_thread = Thread(target=Tello.udp_response_receiver)
            response_receiver_thread.daemon = True
            response_receiver_thread.start()

            # Run state UDP receiver on background
            state_receiver_thread = Thread(target=Tello.udp_state_receiver)
            state_receiver_thread.daemon = True
            state_receiver_thread.start()

            threads_initialized = True

        drones[host] = {'responses': [], 'state': {}}

        self.LOGGER.info("Tello instance was initialized. Host: '{}'. Port: '{}'.".format(host, Tello.CONTROL_UDP_PORT))

        self.vs_udp_port = vs_udp


    def change_vs_udp(self, udp_port):
        """Change the UDP Port for sending video feed from the drone.
        """
        self.vs_udp_port = udp_port
        self.send_control_command(f'port 8890 {self.vs_udp_port}')

    def get_own_udp_object(self):
        """Get own object from the global drones dict. This object is filled
        with responses and state information by the receiver threads.
        Internal method, you normally wouldn't call this yourself.
        """
        global drones

        host = self.address[0]
        return drones[host]

    @staticmethod
    def udp_response_receiver():
        """Setup drone UDP receiver. This method listens for responses of Tello.
        Must be run from a background thread in order to not block the main thread.
        Internal method, you normally wouldn't call this yourself.
        """
        while True:
            try:
                data, address = client_socket.recvfrom(1024)

                address = address[0]
                Tello.LOGGER.debug('Data received from {} at client_socket'.format(address))

                if address not in drones:
                    continue

                drones[address]['responses'].append(data)

            except Exception as e:
                Tello.LOGGER.error(e)
                break

    @staticmethod
    def udp_state_receiver():
        """Setup state UDP receiver. This method listens for state information from
        Tello. Must be run from a background thread in order to not block
        the main thread.
        Internal method, you normally wouldn't call this yourself.
        """
        state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        state_socket.bind(("", Tello.STATE_UDP_PORT))

        while True:
            try:
                data, address = state_socket.recvfrom(1024)

                address = address[0]
                Tello.LOGGER.debug('Data received from {} at state_socket'.format(address))

                if address not in drones:
                    continue

                data = data.decode('ASCII')
                data = Tello.parse_state(data)
                data['received_at'] = datetime.now()
                drones[address]['state'] = data

            except Exception as e:
                Tello.LOGGER.error(e)
                break

    @staticmethod
    def parse_state(state: str) -> Dict[str, Union[int, float, str]]:
        """Parse a state line to a dictionary
        Internal method, you normally wouldn't call this yourself.
        """
        state = state.strip()
        Tello.LOGGER.debug('Raw state data: {}'.format(state))

        if state == 'ok':
            return {}

        state_dict = {}
        for field in state.split(';'):
            split = field.split(':')
            if len(split) < 2:
                continue

            key = split[0]
            value: Union[int, float, str] = split[1]

            if key in Tello.state_field_converters:
                num_type = Tello.state_field_converters[key]
                try:
                    value = num_type(value)
                except ValueError as e:
                    Tello.LOGGER.debug('Error parsing state value for {}: {} to {}'
                                       .format(key, value, num_type))
                    Tello.LOGGER.error(e)
                    continue

            state_dict[key] = value

        return state_dict

    def get_current_state(self) -> dict:
        """Call this function to attain the state of the Tello. Returns a dict
        with all fields.
        Internal method, you normally wouldn't call this yourself.
        """
        return self.get_own_udp_object()['state']

    def get_state_field(self, key: str):
        """Get a specific sate field by name.
        Internal method, you normally wouldn't call this yourself.
        """
        state = self.get_current_state()

        if key in state:
            return state[key]
        else:
            raise TelloException('Could not get state property: {}'.format(key))

    def get_last_state_update(self) -> datetime:
        """Get the datetime of when the last state packet was received.
        You may use this function to check the age of values returned by all other get_* functions.
        Returns:
            datetime: last state update
        """
        return self.get_state_field('received_at')

    def get_mission_pad_id(self) -> int:
        """Mission pad ID of the currently detected mission pad
        Only available on Tello EDUs after calling enable_mission_pads
        Returns:
            int: -1 if none is detected, else 1-8
        """
        return self.get_state_field('mid')

    def get_mission_pad_distance_x(self) -> int:
        """X distance to current mission pad
        Only available on Tello EDUs after calling enable_mission_pads
        Returns:
            int: distance in cm
        """
        return self.get_state_field('x')

    def get_mission_pad_distance_y(self) -> int:
        """Y distance to current mission pad
        Only available on Tello EDUs after calling enable_mission_pads
        Returns:
            int: distance in cm
        """
        return self.get_state_field('y')

    def get_mission_pad_distance_z(self) -> int:
        """Z distance to current mission pad
        Only available on Tello EDUs after calling enable_mission_pads
        Returns:
            int: distance in cm
        """
        return self.get_state_field('z')

    def get_pitch(self) -> int:
        """Get pitch in degree
        Returns:
            int: pitch in degree
        """
        return self.get_state_field('pitch')

    def get_roll(self) -> int:
        """Get roll in degree
        Returns:
            int: roll in degree
        """
        return self.get_state_field('roll')

    def get_yaw(self) -> int:
        """Get yaw in degree
        Returns:
            int: yaw in degree
        """
        return self.get_state_field('yaw')

    def get_speed_x(self) -> int:
        """X-Axis Speed
        Returns:
            int: speed
        """
        return self.get_state_field('vgx')

    def get_speed_y(self) -> int:
        """Y-Axis Speed
        Returns:
            int: speed
        """
        return self.get_state_field('vgy')

    def get_speed_z(self) -> int:
        """Z-Axis Speed
        Returns:
            int: speed
        """
        return self.get_state_field('vgz')

    def get_acceleration_x(self) -> float:
        """X-Axis Acceleration
        Returns:
            float: acceleration
        """
        return self.get_state_field('agx')

    def get_acceleration_y(self) -> float:
        """Y-Axis Acceleration
        Returns:
            float: acceleration
        """
        return self.get_state_field('agy')

    def get_acceleration_z(self) -> float:
        """Z-Axis Acceleration
        Returns:
            float: acceleration
        """
        return self.get_state_field('agz')

    def get_lowest_temperature(self) -> int:
        """Get lowest temperature
        Returns:
            int: lowest temperature (°C)
        """
        return self.get_state_field('templ')

    def get_highest_temperature(self) -> int:
        """Get highest temperature
        Returns:
            float: highest temperature (°C)
        """
        return self.get_state_field('temph')

    def get_temperature(self) -> float:
        """Get average temperature
        Returns:
            float: average temperature (°C)
        """
        templ = self.get_lowest_temperature()
        temph = self.get_highest_temperature()
        return (templ + temph) / 2

    def get_height(self) -> int:
        """Get current height in cm
        Returns:
            int: height in cm
        """
        return self.get_state_field('h')

    def get_distance_tof(self) -> int:
        """Get current distance value from TOF in cm
        Returns:
            int: TOF distance in cm
        """
        return self.get_state_field('tof')

    def get_barometer(self) -> int:
        """Get current barometer measurement in cm
        This resembles the absolute height.
        See https://en.wikipedia.org/wiki/Altimeter
        Returns:
            int: barometer measurement in cm
        """
        return self.get_state_field('baro') * 100

    def get_flight_time(self) -> int:
        """Get the time the motors have been active in seconds
        Returns:
            int: flight time in s
        """
        return self.get_state_field('time')

    def get_battery(self) -> int:
        """Get current battery percentage
        Returns:
            int: 0-100
        """
        return self.get_state_field('bat')

    def get_udp_video_address(self) -> str:
        """Internal method, you normally wouldn't call this youself.
        """
        address_schema = 'udp://@{ip}:{port}'  # + '?overrun_nonfatal=1&fifo_size=5000'
        address = address_schema.format(ip=self.VS_UDP_IP, port=self.vs_udp_port)
        return address

    def get_frame_read(self, with_queue = False, max_queue_len = 32) -> 'BackgroundFrameRead':
        """Get the BackgroundFrameRead object from the camera drone. Then, you just need to call
        backgroundFrameRead.frame to get the actual frame received by the drone.
        Returns:
            BackgroundFrameRead
        """
        if self.background_frame_read is None:
            address = self.get_udp_video_address()
            self.background_frame_read = BackgroundFrameRead(self, address, with_queue, max_queue_len)
            self.background_frame_read.start()
        return self.background_frame_read

    def send_command_with_return(self, command: str, timeout: int = RESPONSE_TIMEOUT) -> str:
        """Send command to Tello and wait for its response.
        Internal method, you normally wouldn't call this yourself.
        Return:
            bool/str: str with response text on success, False when unsuccessfull.
        """
        # Commands very consecutive makes the drone not respond to them.
        # So wait at least self.TIME_BTW_COMMANDS seconds
        diff = time.time() - self.last_received_command_timestamp
        if diff < self.TIME_BTW_COMMANDS:
            self.LOGGER.debug('Waiting {} seconds to execute command: {}...'.format(diff, command))
            time.sleep(diff)

        self.LOGGER.info("Send command: '{}'".format(command))
        timestamp = time.time()

        client_socket.sendto(command.encode('utf-8'), self.address)

        responses = self.get_own_udp_object()['responses']

        while not responses:
            if time.time() - timestamp > timeout:
                message = "Aborting command '{}'. Did not receive a response after {} seconds".format(command, timeout)
                self.LOGGER.warning(message)
                return message
            time.sleep(0.1)  # Sleep during send command

        self.last_received_command_timestamp = time.time()

        first_response = responses.pop(0)  # first datum from socket
        try:
            response = first_response.decode("utf-8")
        except UnicodeDecodeError as e:
            self.LOGGER.error(e)
            return "response decode error"
        response = response.rstrip("\r\n")

        self.LOGGER.info("Response {}: '{}'".format(command, response))
        return response

    def send_command_without_return(self, command: str):
        """Send command to Tello without expecting a response.
        Internal method, you normally wouldn't call this yourself.
        """
        # Commands very consecutive makes the drone not respond to them. So wait at least self.TIME_BTW_COMMANDS seconds

        self.LOGGER.info("Send command (no response expected): '{}'".format(command))
        client_socket.sendto(command.encode('utf-8'), self.address)

    def send_control_command(self, command: str, timeout: int = RESPONSE_TIMEOUT) -> bool:
        """Send control command to Tello and wait for its response.
        Internal method, you normally wouldn't call this yourself.
        """
        response = "max retries exceeded"
        for i in range(0, self.retry_count):
            response = self.send_command_with_return(command, timeout=timeout)

            if 'ok' in response.lower():
                return True

            self.LOGGER.debug("Command attempt #{} failed for command: '{}'".format(i, command))

        self.raise_result_error(command, response)
        return False # never reached

    def send_read_command(self, command: str) -> str:
        """Send given command to Tello and wait for its response.
        Internal method, you normally wouldn't call this yourself.
        """

        response = self.send_command_with_return(command)

        try:
            response = str(response)
        except TypeError as e:
            self.LOGGER.error(e)

        if any(word in response for word in ('error', 'ERROR', 'False')):
            self.raise_result_error(command, response)
            return "Error: this code should never be reached"

        return response

    def send_read_command_int(self, command: str) -> int:
        """Send given command to Tello and wait for its response.
        Parses the response to an integer
        Internal method, you normally wouldn't call this yourself.
        """
        response = self.send_read_command(command)
        return int(response)

    def send_read_command_float(self, command: str) -> float:
        """Send given command to Tello and wait for its response.
        Parses the response to an integer
        Internal method, you normally wouldn't call this yourself.
        """
        response = self.send_read_command(command)
        return float(response)

    def raise_result_error(self, command: str, response: str) -> bool:
        """Used to reaise an error after an unsuccessful command
        Internal method, you normally wouldn't call this yourself.
        """
        tries = 1 + self.retry_count
        raise TelloException("Command '{}' was unsuccessful for {} tries. Latest response:\t'{}'"
                             .format(command, tries, response))

    def connect(self, wait_for_state=True):
        """Enter SDK mode. Call this before any of the control functions.
        """
        self.send_control_command("command")

        if wait_for_state:
            REPS = 20
            for i in range(REPS):
                if self.get_current_state():
                    t = i / REPS  # in seconds
                    Tello.LOGGER.debug("'.connect()' received first state packet after {} seconds".format(t))
                    break
                time.sleep(1 / REPS)

            if not self.get_current_state():
                raise TelloException('Did not receive a state packet from the Tello')

    def send_keepalive(self):
        """Send a keepalive packet to prevent the drone from landing after 15s
        """
        self.send_control_command("keepalive")

    def turn_motor_on(self):
        """Turn on motors without flying (mainly for cooling)
        """
        self.send_control_command("motoron")

    def turn_motor_off(self):
        """Turns off the motor cooling mode
        """
        self.send_control_command("motoroff")

    def initiate_throw_takeoff(self):
        """Allows you to take off by throwing your drone within 5 seconds of this command
        """
        self.send_control_command("throwfly")
        self.is_flying = True

    def takeoff(self):
        """Automatic takeoff.
        """
        # Something it takes a looooot of time to take off and return a succesful takeoff.
        # So we better wait. Otherwise, it would give us an error on the following calls.
        self.send_control_command("takeoff", timeout=Tello.TAKEOFF_TIMEOUT)
        self.is_flying = True

    def land(self):
        """Automatic landing.
        """
        self.send_control_command("land")
        self.is_flying = False

    def streamon(self):
        """Turn on video streaming. Use `tello.get_frame_read` afterwards.
        Video Streaming is supported on all tellos when in AP mode (i.e.
        when your computer is connected to Tello-XXXXXX WiFi ntwork).
        Tello EDUs support video streaming while connected to a
        WiFi-network via SDK 3.

        !!! Note:
            If the response is 'Unknown command' you have to update the Tello
            firmware. This can be done using the official Tello app.
        """
        if self.DEFAULT_VS_UDP_PORT != self.vs_udp_port:
            self.change_vs_udp(self.vs_udp_port)
        self.send_control_command("streamon")
        self.stream_on = True

    def streamoff(self):
        """Turn off video streaming.
        """
        self.send_control_command("streamoff")
        self.stream_on = False

        if self.background_frame_read is not None:
            self.background_frame_read.stop()
            self.background_frame_read = None

    def emergency(self):
        """Stop all motors immediately.
        """
        self.send_command_without_return("emergency")
        self.is_flying = False

    def move(self, direction: str, x: int):
        """Tello fly up, down, left, right, forward or back with distance x cm.
        Users would normally call one of the move_x functions instead.
        Arguments:
            direction: up, down, left, right, forward or back
            x: 20-500
        """
        self.send_control_command("{} {}".format(direction, x))

    def move_up(self, x: int):
        """Fly x cm up.
        Arguments:
            x: 20-500
        """
        self.move("up", x)

    def move_down(self, x: int):
        """Fly x cm down.
        Arguments:
            x: 20-500
        """
        self.move("down", x)

    def move_left(self, x: int):
        """Fly x cm left.
        Arguments:
            x: 20-500
        """
        self.move("left", x)

    def move_right(self, x: int):
        """Fly x cm right.
        Arguments:
            x: 20-500
        """
        self.move("right", x)

    def move_forward(self, x: int):
        """Fly x cm forward.
        Arguments:
            x: 20-500
        """
        self.move("forward", x)

    def move_back(self, x: int):
        """Fly x cm backwards.
        Arguments:
            x: 20-500
        """
        self.move("back", x)

    def rotate_clockwise(self, x: int):
        """Rotate x degree clockwise.
        Arguments:
            x: 1-360
        """
        self.send_control_command("cw {}".format(x))

    def rotate_counter_clockwise(self, x: int):
        """Rotate x degree counter-clockwise.
        Arguments:
            x: 1-3600
        """
        self.send_control_command("ccw {}".format(x))

    def flip(self, direction: str):
        """Do a flip maneuver.
        Users would normally call one of the flip_x functions instead.
        Arguments:
            direction: l (left), r (right), f (forward) or b (back)
        """
        self.send_control_command("flip {}".format(direction))

    def flip_left(self):
        """Flip to the left.
        """
        self.flip("l")

    def flip_right(self):
        """Flip to the right.
        """
        self.flip("r")

    def flip_forward(self):
        """Flip forward.
        """
        self.flip("f")

    def flip_back(self):
        """Flip backwards.
        """
        self.flip("b")

    def go_xyz_speed(self, x: int, y: int, z: int, speed: int):
        """Fly to x y z relative to the current position.
        Speed defines the traveling speed in cm/s.
        Arguments:
            x: -500-500
            y: -500-500
            z: -500-500
            speed: 10-100
        """
        cmd = 'go {} {} {} {}'.format(x, y, z, speed)
        self.send_control_command(cmd)

    def stop(self):
        """Hovers in the air. Works at any time.
        """
        self.send_control_command("stop")

    def curve_xyz_speed(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int):
        """Fly to x2 y2 z2 in a curve via x1 y1 z1. Speed defines the traveling speed in cm/s.

        - Both points are relative to the current position
        - The current position and both points must form a circle arc.
        - If the arc radius is not within the range of 0.5-10 meters, it raises an Exception
        - x1/x2, y1/y2, z1/z2 can't both be between -20-20 at the same time, but can both be 0.

        Arguments:
            x1: -500-500
            x2: -500-500
            y1: -500-500
            y2: -500-500
            z1: -500-500
            z2: -500-500
            speed: 10-60
        """
        cmd = 'curve {} {} {} {} {} {} {}'.format(x1, y1, z1, x2, y2, z2, speed)
        self.send_control_command(cmd)

    def go_xyz_speed_mid(self, x: int, y: int, z: int, speed: int, mid: int):
        """Fly to x y z relative to the mission pad with id mid.
        Speed defines the traveling speed in cm/s.
        Arguments:
            x: -500-500
            y: -500-500
            z: -500-500
            speed: 10-100
            mid: 1-8
        """
        cmd = 'go {} {} {} {} m{}'.format(x, y, z, speed, mid)
        self.send_control_command(cmd)

    def curve_xyz_speed_mid(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int, mid: int):
        """Fly to x2 y2 z2 in a curve via x1 y1 z1. Speed defines the traveling speed in cm/s.

        - Both points are relative to the mission pad with id mid.
        - The current position and both points must form a circle arc.
        - If the arc radius is not within the range of 0.5-10 meters, it raises an Exception
        - x1/x2, y1/y2, z1/z2 can't both be between -20-20 at the same time, but can both be 0.

        Arguments:
            x1: -500-500
            y1: -500-500
            z1: -500-500
            x2: -500-500
            y2: -500-500
            z2: -500-500
            speed: 10-60
            mid: 1-8
        """
        cmd = 'curve {} {} {} {} {} {} {} m{}'.format(x1, y1, z1, x2, y2, z2, speed, mid)
        self.send_control_command(cmd)

    def go_xyz_speed_yaw_mid(self, x: int, y: int, z: int, speed: int, yaw: int, mid1: int, mid2: int):
        """Fly to x y z relative to mid1.
        Then fly to 0 0 z over mid2 and rotate to yaw relative to mid2's rotation.
        Speed defines the traveling speed in cm/s.
        Arguments:
            x: -500-500
            y: -500-500
            z: -500-500
            speed: 10-100
            yaw: -360-360
            mid1: 1-8
            mid2: 1-8
        """
        cmd = 'jump {} {} {} {} {} m{} m{}'.format(x, y, z, speed, yaw, mid1, mid2)
        self.send_control_command(cmd)

    def enable_mission_pads(self):
        """Enable mission pad detection
        """
        self.send_control_command("mon")

    def disable_mission_pads(self):
        """Disable mission pad detection
        """
        self.send_control_command("moff")

    def set_mission_pad_detection_direction(self, x):
        """Set mission pad detection direction. enable_mission_pads needs to be
        called first. When detecting both directions detecting frequency is 10Hz,
        otherwise the detection frequency is 20Hz.
        Arguments:
            x: 0 downwards only, 1 forwards only, 2 both directions
        """
        self.send_control_command("mdirection {}".format(x))

    def set_speed(self, x: int):
        """Set speed to x cm/s.
        Arguments:
            x: 10-100
        """
        self.send_control_command("speed {}".format(x))

    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int,
                        yaw_velocity: int):
        """Send RC control via four channels. Command is sent every self.TIME_BTW_RC_CONTROL_COMMANDS seconds.
        Arguments:
            left_right_velocity: -100~100 (left/right)
            forward_backward_velocity: -100~100 (forward/backward)
            up_down_velocity: -100~100 (up/down)
            yaw_velocity: -100~100 (yaw)
        """
        def clamp100(x: int) -> int:
            return max(-100, min(100, x))

        if time.time() - self.last_rc_control_timestamp > self.TIME_BTW_RC_CONTROL_COMMANDS:
            self.last_rc_control_timestamp = time.time()
            cmd = 'rc {} {} {} {}'.format(
                clamp100(left_right_velocity),
                clamp100(forward_backward_velocity),
                clamp100(up_down_velocity),
                clamp100(yaw_velocity)
            )
            self.send_command_without_return(cmd)

    def set_wifi_credentials(self, ssid: str, password: str):
        """Set the Wi-Fi SSID and password. The Tello will reboot afterwords.
        """
        cmd = 'wifi {} {}'.format(ssid, password)
        self.send_control_command(cmd)

    def connect_to_wifi(self, ssid: str, password: str):
        """Connects to the Wi-Fi with SSID and password.
        After this command the tello will reboot.
        Only works with Tello EDUs.
        """
        cmd = 'ap {} {}'.format(ssid, password)
        self.send_control_command(cmd)

    def set_network_ports(self, state_packet_port: int, video_stream_port: int):
        """Sets the ports for state packets and video streaming
        While you can use this command to reconfigure the Tello this library currently does not support
        non-default ports (TODO!)
        """
        cmd = 'port {} {}'.format(state_packet_port, video_stream_port)
        self.send_control_command(cmd)

    def reboot(self):
        """Reboots the drone
        """
        self.send_command_without_return('reboot')

    def set_video_bitrate(self, bitrate: int):
        """Sets the bitrate of the video stream
        Use one of the following for the bitrate argument:
            Tello.BITRATE_AUTO
            Tello.BITRATE_1MBPS
            Tello.BITRATE_2MBPS
            Tello.BITRATE_3MBPS
            Tello.BITRATE_4MBPS
            Tello.BITRATE_5MBPS
        """
        cmd = 'setbitrate {}'.format(bitrate)
        self.send_control_command(cmd)

    def set_video_resolution(self, resolution: str):
        """Sets the resolution of the video stream
        Use one of the following for the resolution argument:
            Tello.RESOLUTION_480P
            Tello.RESOLUTION_720P
        """
        cmd = 'setresolution {}'.format(resolution)
        self.send_control_command(cmd)

    def set_video_fps(self, fps: str):
        """Sets the frames per second of the video stream
        Use one of the following for the fps argument:
            Tello.FPS_5
            Tello.FPS_15
            Tello.FPS_30
        """
        cmd = 'setfps {}'.format(fps)
        self.send_control_command(cmd)

    def set_video_direction(self, direction: int):
        """Selects one of the two cameras for video streaming
        The forward camera is the regular 1080x720 color camera
        The downward camera is a grey-only 320x240 IR-sensitive camera
        Use one of the following for the direction argument:
            Tello.CAMERA_FORWARD
            Tello.CAMERA_DOWNWARD
        """
        cmd = 'downvision {}'.format(direction)
        self.send_control_command(cmd)

    def send_expansion_command(self, expansion_cmd: str):
        """Sends a command to the ESP32 expansion board connected to a Tello Talent
        Use e.g. tello.send_expansion_command("led 255 0 0") to turn the top led red.
        """
        cmd = 'EXT {}'.format(expansion_cmd)
        self.send_control_command(cmd)

    def query_speed(self) -> int:
        """Query speed setting (cm/s)
        Returns:
            int: 1-100
        """
        return self.send_read_command_int('speed?')

    def query_battery(self) -> int:
        """Get current battery percentage via a query command
        Using get_battery is usually faster
        Returns:
            int: 0-100 in %
        """
        return self.send_read_command_int('battery?')

    def query_flight_time(self) -> int:
        """Query current fly time (s).
        Using get_flight_time is usually faster.
        Returns:
            int: Seconds elapsed during flight.
        """
        return self.send_read_command_int('time?')

    def query_height(self) -> int:
        """Get height in cm via a query command.
        Using get_height is usually faster
        Returns:
            int: 0-3000
        """
        return self.send_read_command_int('height?')

    def query_temperature(self) -> int:
        """Query temperature (°C).
        Using get_temperature is usually faster.
        Returns:
            int: 0-90
        """
        return self.send_read_command_int('temp?')

    def query_attitude(self) -> dict:
        """Query IMU attitude data.
        Using get_pitch, get_roll and get_yaw is usually faster.
        Returns:
            {'pitch': int, 'roll': int, 'yaw': int}
        """
        response = self.send_read_command('attitude?')
        return Tello.parse_state(response)

    def query_barometer(self) -> int:
        """Get barometer value (cm)
        Using get_barometer is usually faster.
        Returns:
            int: 0-100
        """
        baro = self.send_read_command_int('baro?')
        return baro * 100

    def query_distance_tof(self) -> float:
        """Get distance value from TOF (cm)
        Using get_distance_tof is usually faster.
        Returns:
            float: 30-1000
        """
        # example response: 801mm
        tof = self.send_read_command('tof?')
        return int(tof[:-2]) / 10

    def query_wifi_signal_noise_ratio(self) -> str:
        """Get Wi-Fi SNR
        Returns:
            str: snr
        """
        return self.send_read_command('wifi?')

    def query_sdk_version(self) -> str:
        """Get SDK Version
        Returns:
            str: SDK Version
        """
        return self.send_read_command('sdk?')

    def query_serial_number(self) -> str:
        """Get Serial Number
        Returns:
            str: Serial Number
        """
        return self.send_read_command('sn?')

    def query_active(self) -> str:
        """Get the active status
        Returns:
            str
        """
        return self.send_read_command('active?')

    def end(self):
        """Call this method when you want to end the tello object
        """
        try:
            if self.is_flying:
                self.land()
            if self.stream_on:
                self.streamoff()
        except TelloException:
            pass

        if self.background_frame_read is not None:
            self.background_frame_read.stop()
            self.background_frame_read = None

        host = self.address[0]
        if host in drones:
            del drones[host]

    def __del__(self):
        self.end()


class BackgroundFrameRead:
    """
    This class read frames using PyAV in background. Use
    backgroundFrameRead.frame to get the current frame.
    """

    def __init__(self, tello, address, with_queue = False, maxsize = 32):
        self.address = address
        self.lock = Lock()
        self.frame = np.zeros([300, 400, 3], dtype=np.uint8)
        self.frames = deque([], maxsize)
        self.with_queue = with_queue

        # Try grabbing frame with PyAV
        # According to issue #90 the decoder might need some time
        # https://github.com/damiafuentes/DJITelloPy/issues/90#issuecomment-855458905
        try:
            Tello.LOGGER.debug('trying to grab video frames...')
            self.container = av.open(self.address, timeout=(Tello.FRAME_GRAB_TIMEOUT, None))
        except av.error.ExitError:
            raise TelloException('Failed to grab video frames from video stream')

        self.stopped = False
        self.worker = Thread(target=self.update_frame, args=(), daemon=True)

    def start(self):
        """Start the frame update worker
        Internal method, you normally wouldn't call this yourself.
        """
        self.worker.start()

    def update_frame(self):
        """Thread worker function to retrieve frames using PyAV
        Internal method, you normally wouldn't call this yourself.
        """
        try:
            for frame in self.container.decode(video=0):
                if self.with_queue:
                    self.frames.append(np.array(frame.to_image()))
                else:
                    self.frame = np.array(frame.to_image())

                if self.stopped:
                    self.container.close()
                    break
        except av.error.ExitError:
            raise TelloException('Do not have enough frames for decoding, please try again or increase video fps before get_frame_read()')
    
    def get_queued_frame(self):
        """
        Get a frame from the queue
        """
        with self.lock:
            try:
                return self.frames.popleft()
            except IndexError:
                return None

    @property
    def frame(self):
        """
        Access the frame variable directly
        """
        if self.with_queue:
            return self.get_queued_frame()

        with self.lock:
            return self._frame

    @frame.setter
    def frame(self, value):
        with self.lock:
            self._frame = value

    def stop(self):
        """Stop the frame update worker
        Internal method, you normally wouldn't call this yourself.
        """
        self.stopped = True
