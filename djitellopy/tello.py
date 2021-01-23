# coding=utf-8
import logging
import socket
import time
import threading
import cv2 # type: ignore
from threading import Thread
from typing import Optional

from .enforce_types import enforce_types


threads_initialized = False
drones: Optional[dict] = {}
client_socket: socket.socket


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
    TIME_BTW_COMMANDS = 0.1  # in seconds
    TIME_BTW_RC_CONTROL_COMMANDS = 0.001  # in seconds
    RETRY_COUNT = 3  # number of retries after a failed command
    TELLO_IP = '192.168.10.1'  # Tello IP address

    # Video stream, server socket
    VS_UDP_IP = '0.0.0.0'
    VS_UDP_PORT = 11111

    CONTROL_UDP_PORT = 8889
    STATE_UDP_PORT = 8890

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
    state_field_converters = {key : int for key in INT_STATE_FIELDS}
    state_field_converters.update({key : float for key in FLOAT_STATE_FIELDS})

    # VideoCapture object
    cap: Optional[cv2.VideoCapture] = None
    background_frame_read: Optional['BackgroundFrameRead'] = None

    stream_on = False
    is_flying = False

    def __init__(self,
                 host=TELLO_IP,
                 retry_count=RETRY_COUNT):

        global threads_initialized, client_socket, drones

        self.address = (host, Tello.CONTROL_UDP_PORT)
        self.stream_on = False
        self.retry_count = retry_count
        self.last_received_command_timestamp = time.time()
        self.last_rc_control_timestamp = time.time()

        if not threads_initialized:
            # Run Tello command responses UDP receiver on background
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.bind(('', Tello.CONTROL_UDP_PORT))
            response_receiver_thread = threading.Thread(target=Tello.udp_response_receiver)
            response_receiver_thread.daemon = True
            response_receiver_thread.start()

            # Run state UDP receiver on background
            state_receiver_thread = threading.Thread(target=Tello.udp_state_receiver)
            state_receiver_thread.daemon = True
            state_receiver_thread.start()

            threads_initialized = True

        drones[host] = {'responses': [], 'state': {}}

        self.LOGGER.info("Tello instance was initialized. Host: '{}'. Port: '{}'.".format(host, Tello.CONTROL_UDP_PORT))

    def get_own_udp_object(self):
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
                drones[address]['state'] = Tello.parse_state(data)

            except Exception as e:
                Tello.LOGGER.error(e)
                break

    @staticmethod
    def parse_state(state: str) -> dict:
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
            value = split[1]

            if key in Tello.state_field_converters:
                num_type = Tello.state_field_converters[key]
                try:
                    value = num_type(value)
                except Exception as e:
                    Tello.LOGGER.debug('Error parsing state value for {}: {} to {}'
                                       .format(key, value, num_type))
                    Tello.LOGGER.error(e)

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
            raise Exception('Could not get state property: {}'.format(key))

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
        address = address_schema.format(ip=self.VS_UDP_IP, port=self.VS_UDP_PORT)
        return address

    def get_video_capture(self):
        """Get the VideoCapture object from the camera drone.
        Users usually want to use get_frame_read instead.
        Returns:
            VideoCapture
        """

        if self.cap is None:
            self.cap = cv2.VideoCapture(self.get_udp_video_address())

        if not self.cap.isOpened():
            self.cap.open(self.get_udp_video_address())

        return self.cap

    def get_frame_read(self) -> 'BackgroundFrameRead':
        """Get the BackgroundFrameRead object from the camera drone. Then, you just need to call
        backgroundFrameRead.frame to get the actual frame received by the drone.
        Returns:
            BackgroundFrameRead
        """
        if self.background_frame_read is None:
            address = self.get_udp_video_address()
            self.background_frame_read = BackgroundFrameRead(self, address)  # also sets self.cap
            self.background_frame_read.start()
        return self.background_frame_read

    def stop_video_capture(self):
        return self.streamoff()

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
            self.sleep(diff)

        self.LOGGER.info("Send command: '{}'".format(command))
        timestamp = time.time()

        client_socket.sendto(command.encode('utf-8'), self.address)

        responses = self.get_own_udp_object()['responses']

        while not responses:
            if time.time() - timestamp > timeout:
                message = "Aborting command '{}'. Did not receive a response after {} seconds".format(command, timeout)
                self.LOGGER.warning(message)
                return message
            self.sleep(0.1)  # Sleep during send command

        self.last_received_command_timestamp = time.time()

        first_response = responses.pop(0)  # first datum from socket
        try:
            response_decoded = first_response.decode('utf-8')
        except UnicodeDecodeError as e:
            pass
            #print(e)
            #print(response_0)
        response = response_decoded.rstrip("\r\n")

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

            if response.lower() == 'ok':
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
            pass

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
        tries = 1 + self.retry_count
        raise Exception("Command '{}' was unsuccessful for {} tries. Latest response:\t'{}'".format(command, tries, response))

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
                self.sleep(1 / REPS)

            if not self.get_current_state():
                raise Exception('Did not receive a state packet from the Tello')

    def sleep(time_sleep=5):
        """Sleep.
        """
        time.sleep(time_sleep)

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
        Currently Tello EDUs do not support video streaming while connected
        to a WiFi-network.

        !!! Note:
            If the response is 'Unknown command' you have to update the Tello
            firmware. This can be done using the official Tello app.
        """
        self.send_control_command("streamon")
        self.stream_on = True

    def streamoff(self):
        """Turn off video streaming.
        """
        self.send_control_command("streamoff")
        self.stream_on = False

    def emergency(self):
        """Stop all motors immediately.
        """
        self.send_control_command("emergency")

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
            x: 20-500
            y: 20-500
            z: 20-500
            speed: 10-100
        """
        SCHEMA = 'go %s %s %s %s'
        self.send_control_command(SCHEMA % (x, y, z, speed))

    def curve_xyz_speed(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int):
        """Fly to x2 y2 z2 in a curve via x2 y2 z2. Speed defines the traveling speed in cm/s.

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
        SCHEMA = 'curve %s %s %s %s %s %s %s'
        self.send_control_command(SCHEMA % (x1, y1, z1, x2, y2, z2, speed))

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
        SCHEMA = 'go %s %s %s %s m%s'
        self.send_control_command(SCHEMA % (x, y, z, speed, mid))

    def curve_xyz_speed_mid(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int, mid: int):
        """Fly to x2 y2 z2 in a curve via x2 y2 z2. Speed defines the traveling speed in cm/s.

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
        SCHEMA = 'curve %s %s %s %s %s %s %s m%s'
        self.send_control_command(SCHEMA % (x1, y1, z1, x2, y2, z2, speed, mid))

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
        SCHEMA = 'jump %s %s %s %s %s m%s m%s'
        self.send_control_command(SCHEMA % (x, y, z, speed, yaw, mid1, mid2))

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
        def round_to_100(x: int):
            return max(-100, min(100, x))

        if time.time() - self.last_rc_control_timestamp > self.TIME_BTW_RC_CONTROL_COMMANDS:
            self.last_rc_control_timestamp = time.time()
            SCHEMA = 'rc %s %s %s %s'
            self.send_command_without_return(SCHEMA % (round_to_100(left_right_velocity),
                round_to_100(forward_backward_velocity),
                round_to_100(up_down_velocity),
                round_to_100(yaw_velocity)))

    def set_wifi_credentials(self, ssid, password):
        """Set the Wi-Fi SSID and password. The Tello will reboot afterwords.
        """
        SCHEMA = 'wifi %s %s'
        self.send_command_without_return(SCHEMA % (ssid, password))

    def connect_to_wifi(self, ssid, password):
        """Connects to the Wi-Fi with SSID and password.
        After this command the tello will reboot.
        Only works with Tello EDUs.
        """
        SCHEMA = 'ap %s %s'
        self.send_command_without_return(SCHEMA % (ssid, password))

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

    def end(self):
        """Call this method when you want to end the tello object
        """
        if self.is_flying:
            self.land()
        if self.stream_on:
            self.streamoff()
        if self.background_frame_read is not None:
            self.background_frame_read.stop()
        if self.cap is not None:
            self.cap.release()

        host = self.address[0]
        if host in drones:
            del drones[host]

    def __del__(self):
        self.end()


class BackgroundFrameRead:
    """
    This class read frames from a VideoCapture in background. Use
    backgroundFrameRead.frame to get the current frame.
    """

    def __init__(self, tello, address):
        tello.cap = cv2.VideoCapture(address)

        self.cap = tello.cap

        if not self.cap.isOpened():
            self.cap.open(address)

        self.grabbed, self.frame = self.cap.read()
        if not self.grabbed or self.frame is None:
            raise Exception('Failed to grab first frame from video stream')

        self.stopped = False
        self.worker = Thread(target=self.update_frame, args=(), daemon=True)

    def start(self):
        self.worker.start()

    def update_frame(self):
        while not self.stopped:
            if not self.grabbed or not self.cap.isOpened():
                self.stop()
            else:
                self.grabbed, self.frame = self.cap.read()

    def stop(self):
        self.stopped = True
        self.worker.join()
