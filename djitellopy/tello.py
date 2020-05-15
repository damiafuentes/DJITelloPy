# coding=utf-8
import logging
import socket
import time
import threading
import cv2
from threading import Thread

drones = None
client_socket = None


class Tello:
    """Python wrapper to interact with the Ryze Tello drone using the official Tello api.
    Tello API documentation:
    https://dl-cdn.ryzerobotics.com/downloads/tello/20180910/Tello%20SDK%20Documentation%20EN_1.3.pdf
    https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf
    """
    # Send and receive commands, client socket
    RESPONSE_TIMEOUT = 7  # in seconds
    TIME_BTW_COMMANDS = 1  # in seconds
    TIME_BTW_RC_CONTROL_COMMANDS = 0.5  # in seconds
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
    # use Tello.LOGGER.setLevel(logging.<LEVEL>) in YOUR CODE
    # to only receive logs of the desired level and higher

    # conversion functions for state protocol fields
    state_field_converters = {
        # Tello EDU with mission pads enabled only
        'mid': int,
        'x': int,
        'y': int,
        'z': int,
        # 'mpry': (custom format 'x,y,z')

        # common entries
        'pitch': int,
        'roll': int,
        'yaw': int,
        'vgx': int,
        'vgy': int,
        'vgz': int,
        'templ': int,
        'temph': int,
        'tof': int,
        'h': int,
        'bat': int,
        'baro': float,
        'time': int,
        'agx': float,
        'agy': float,
        'agz': float,
    }

    # VideoCapture object
    cap = None
    background_frame_read = None

    stream_on = False
    is_flying = False

    def __init__(self,
                 host=TELLO_IP,
                 retry_count=RETRY_COUNT):

        global drones

        self.address = (host, Tello.CONTROL_UDP_PORT)
        self.stream_on = False
        self.retry_count = retry_count
        self.last_received_command_timestamp = time.time()
        self.last_rc_control_timestamp = time.time()

        if drones is None:
            drones = {}

            # Run Tello command responses UDP receiver on background
            response_receiver_thread = threading.Thread(target=Tello.udp_response_receiver)
            response_receiver_thread.daemon = True
            response_receiver_thread.start()

            # Run state UDP receiver on background
            state_receiver_thread = threading.Thread(target=Tello.udp_state_receiver)
            state_receiver_thread.daemon = True
            state_receiver_thread.start()

        drones[host] = {
            'responses': [],
            'state': {},
        }

    def get_own_udp_object(self):
        global drones

        host = self.address[0]
        return drones[host]

    @staticmethod
    def udp_response_receiver():
        """Setup drone UDP receiver. This method listens for responses of Tello.
        Must be run from a background thread in order to not block the main thread."""
        global client_socket

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.bind(('', Tello.CONTROL_UDP_PORT))

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
        the main thread."""
        state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        state_socket.bind(('', Tello.STATE_UDP_PORT))

        while True:
            try:
                data, address = state_socket.recvfrom(1024)

                address = address[0]
                Tello.LOGGER.debug('Data received from {} at state_socket'.format(address))

                if address not in drones:
                    continue

                drones[address]['state'] = Tello.parse_state(data)

            except Exception as e:
                Tello.LOGGER.error(e)
                break

    @staticmethod
    def parse_state(state: str) -> dict:
        """Parse a state line to a dictionary"""
        state = state.decode('ASCII').strip()
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
                try:
                    value = Tello.state_field_converters[key](value)
                except Exception as e:
                    Tello.LOGGER.debug('Error parsing state value for {}: {} to {}'
                                       .format(key, value, Tello.state_field_converters[key]))
                    Tello.LOGGER.error(e)

            state_dict[key] = value

        return state_dict

    def get_current_state(self) -> dict:
        """Call this function to attain the state of the Tello. Returns a dict
        with all fields"""
        return self.get_own_udp_object()['state']

    def get_state_field(self, key: str) -> any:
        state = self.get_current_state()

        if key in state:
            return state[key]
        else:
            raise Exception('Could not get state property ' + key)

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

    def get_height(self) -> int:
        """Get current height in cm
        Returns:
            int: height in cm
        """
        return self.get_state_field('h')

    def get_battery(self) -> int:
        """Get current battery percentage
        Returns:
            False: Unsuccessful
            int: 0-100
        """
        return self.get_state_field('bat')

    def get_udp_video_address(self) -> str:
        return 'udp://@' + self.VS_UDP_IP + ':' + str(self.VS_UDP_PORT)  # + '?overrun_nonfatal=1&fifo_size=5000'

    def get_video_capture(self):
        """Get the VideoCapture object from the camera drone
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
            self.background_frame_read = BackgroundFrameRead(self, self.get_udp_video_address()).start()
        return self.background_frame_read

    def stop_video_capture(self):
        return self.streamoff()

    def send_command_with_return(self, command: str, timeout: int = RESPONSE_TIMEOUT) -> str:
        """Send command to Tello and wait for its response.
        Return:
            bool: True for successful, False for unsuccessful
        """
        # Commands very consecutive makes the drone not respond to them. So wait at least self.TIME_BTW_COMMANDS seconds
        diff = time.time() - self.last_received_command_timestamp
        if diff < self.TIME_BTW_COMMANDS:
            self.LOGGER.debug('Waiting {} seconds to execute command {}...'.format(diff, command))
            time.sleep(diff)

        self.LOGGER.info('Send command: ' + command)
        timestamp = time.time()

        client_socket.sendto(command.encode('utf-8'), self.address)

        responses = self.get_own_udp_object()['responses']
        while len(responses) == 0:
            if time.time() - timestamp > timeout:
                self.LOGGER.warning('Timeout exceed on command ' + command)
                return False
            else:
                time.sleep(0.1)

        self.last_received_command_timestamp = time.time()
        response = responses.pop(0)
        response = response.decode('utf-8').rstrip("\r\n")

        self.LOGGER.info('Response {}: {}'.format(command, response))

        return response

    def send_command_without_return(self, command: str):
        """Send command to Tello without expecting a response. Use this method when you want to send a command
        continuously
            - go x y z speed: Tello fly to x y z in speed (cm/s)
                x: 20-500
                y: 20-500
                z: 20-500
                speed: 10-100
            - curve x1 y1 z1 x2 y2 z2 speed: Tello fly a curve defined by the current and two given coordinates with
                speed (cm/s). If the arc radius is not within the range of 0.5-10 meters, it responses false.
                x/y/z can’t be between -20 – 20 at the same time .
                x1, x2: 20-500
                y1, y2: 20-500
                z1, z2: 20-500
                speed: 10-60
            - rc a b c d: Send RC control via four channels.
                a: left/right (-100~100)
                b: forward/backward (-100~100)
                c: up/down (-100~100)
                d: yaw (-100~100)
        """
        # Commands very consecutive makes the drone not respond to them. So wait at least self.TIME_BTW_COMMANDS seconds

        self.LOGGER.info('Send command (no expect response): ' + command)
        client_socket.sendto(command.encode('utf-8'), self.address)

    def send_control_command(self, command: str, timeout: int = RESPONSE_TIMEOUT) -> str:
        """Send control command to Tello and wait for its response. Possible control commands:
            - command: entry SDK mode
            - takeoff: Tello auto takeoff
            - land: Tello auto land
            - streamon: Set video stream on
            - streamoff: Set video stream off
            - emergency: Stop all motors immediately
            - up x: Tello fly up with distance x cm. x: 20-500
            - down x: Tello fly down with distance x cm. x: 20-500
            - left x: Tello fly left with distance x cm. x: 20-500
            - right x: Tello fly right with distance x cm. x: 20-500
            - forward x: Tello fly forward with distance x cm. x: 20-500
            - back x: Tello fly back with distance x cm. x: 20-500
            - cw x: Tello rotate x degree clockwise x: 1-3600
            - ccw x: Tello rotate x degree counter- clockwise. x: 1-3600
            - flip x: Tello fly flip x
                l (left)
                r (right)
                f (forward)
                b (back)
            - speed x: set speed to x cm/s. x: 10-100
            - wifi ssid pass: Set Wi-Fi with SSID password

        Return:
            bool: True for successful, False for unsuccessful
        """
        response = None
        for i in range(0, self.retry_count):
            response = self.send_command_with_return(command, timeout=timeout)

            if response == 'OK' or response == 'ok':
                return True

            self.LOGGER.debug('Command attempt {} for {} failed'.format(i, command))

        return self.raise_result_error(command, response)

    def send_read_command(self, command: str) -> str:
        """Send set command to Tello and wait for its response. Possible set commands:
            - speed?: get current speed (cm/s): x: 1-100
            - battery?: get current battery percentage: x: 0-100
            - time?: get current fly time (s): time
            - height?: get height (cm): x: 0-3000
            - temp?: get temperature (°C): x: 0-90
            - attitude?: get IMU attitude data: pitch roll yaw
            - baro?: get barometer value (m): x
            - tof?: get distance value from TOF (cm): x: 30-1000
            - wifi?: get Wi-Fi SNR: snr

        Return:
            bool: The requested value for successful, False for unsuccessful
        """

        response = self.send_command_with_return(command)

        try:
            response = str(response)
        except TypeError as e:
            self.LOGGER.error(e)
            pass

        if ('error' not in response) and ('ERROR' not in response) and ('False' not in response):
            if response.isdigit():
                return int(response)
            else:
                try:
                    return float(response)  # isdigit() is False when the number is a float(barometer)
                except ValueError:
                    return response
        else:
            return self.raise_result_error(command, response)

    def raise_result_error(self, command: str, response: any) -> bool:
        raise Exception('Command {} was unsuccessful. Message: {}'.format(command, response))

    def connect(self):
        """Entry SDK mode
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("command")

    def takeoff(self):
        """Tello auto takeoff
        Returns:
            bool: True for successful, False for unsuccessful
            False: Unsuccessful
        """
        # Something it takes a looooot of time to take off and return a succesful take off.
        # So we better wait. If not, is going to give us error on the following calls.
        if self.send_control_command("takeoff", timeout=20):
            self.is_flying = True
            return True
        else:
            return False

    def land(self):
        """Tello auto land
        Returns:
            bool: True for successful, False for unsuccessful
        """
        if self.send_control_command("land"):
            self.is_flying = False
            return True
        else:
            return False

    def streamon(self):
        """Set video stream on. If the response is 'Unknown command' means you have to update the Tello firmware.
        That can be done through the Tello app.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        result = self.send_control_command("streamon")
        if result is True:
            self.stream_on = True
        return result

    def streamoff(self):
        """Set video stream off
        Returns:
            bool: True for successful, False for unsuccessful
        """
        result = self.send_control_command("streamoff")
        if result is True:
            self.stream_on = False
        return result

    def emergency(self):
        """Stop all motors immediately
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("emergency")

    def move(self, direction: str, x: int):
        """Tello fly up, down, left, right, forward or back with distance x cm.
        Arguments:
            direction: up, down, left, right, forward or back
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command(direction + ' ' + str(x))

    def move_up(self, x: int):
        """Tello fly up with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("up", x)

    def move_down(self, x: int):
        """Tello fly down with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("down", x)

    def move_left(self, x: int):
        """Tello fly left with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("left", x)

    def move_right(self, x: int):
        """Tello fly right with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("right", x)

    def move_forward(self, x: int):
        """Tello fly forward with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("forward", x)

    def move_back(self, x: int):
        """Tello fly back with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("back", x)

    def rotate_clockwise(self, x: int):
        """Tello rotate x degree clockwise.
        Arguments:
            x: 1-360

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("cw " + str(x))

    def rotate_counter_clockwise(self, x: int):
        """Tello rotate x degree counter-clockwise.
        Arguments:
            x: 1-3600

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("ccw " + str(x))

    def flip(self, direction: str):
        """Tello fly flip.
        Arguments:
            direction: l (left), r (right), f (forward) or b (back)

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("flip " + direction)

    def flip_left(self):
        """Tello fly flip left.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.flip("l")

    def flip_right(self):
        """Tello fly flip left.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.flip("r")

    def flip_forward(self):
        """Tello fly flip left.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.flip("f")

    def flip_back(self):
        """Tello fly flip left.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.flip("b")

    def go_xyz_speed(self, x: int, y: int, z: int, speed: int):
        """Tello fly to x y z in speed (cm/s)
        Arguments:
            x: 20-500
            y: 20-500
            z: 20-500
            speed: 10-100
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_command_without_return('go %s %s %s %s' % (x, y, z, speed))

    def curve_xyz_speed(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int):
        """Tello fly a curve defined by the current and two given coordinates with speed (cm/s).
            - If the arc radius is not within the range of 0.5-10 meters, it responses false.
            - x/y/z can’t be between -20 – 20 at the same time.
        Arguments:
            x1: 20-500
            x2: 20-500
            y1: 20-500
            y2: 20-500
            z1: 20-500
            z2: 20-500
            speed: 10-60
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_command_without_return('curve %s %s %s %s %s %s %s' % (x1, y1, z1, x2, y2, z2, speed))

    def go_xyz_speed_mid(self, x: int, y: int, z: int, speed: int, mid: int):
        """Tello fly to x y z in speed (cm/s) relative to mission pad iwth id mid
        Arguments:
            x: -500-500
            y: -500-500
            z: -500-500
            speed: 10-100
            mid: 1-8
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command('go %s %s %s %s m%s' % (x, y, z, speed, mid))

    def curve_xyz_speed_mid(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int, mid: int):
        """Tello fly to x2 y2 z2 over x1 y1 z1 in speed (cm/s) relative to mission pad with id mid
        Arguments:
            x1: -500-500
            y1: -500-500
            z1: -500-500
            x2: -500-500
            y2: -500-500
            z2: -500-500
            speed: 10-60
            mid: 1-8
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command('curve %s %s %s %s %s %s %s m%s' % (x1, y1, z1, x2, y2, z2, speed, mid))

    def go_xyz_speed_yaw_mid(self, x: int, y: int, z: int, speed: int, yaw: int, mid1: int, mid2: int):
        """Tello fly to x y z in speed (cm/s) relative to mid1
        Then fly to 0 0 z over mid2 and rotate to yaw relative to mid2's rotation
        Arguments:
            x: -500-500
            y: -500-500
            z: -500-500
            speed: 10-100
            yaw: -360-360
            mid1: 1-8
            mid2: 1-8
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command('jump %s %s %s %s %s m%s m%s' % (x, y, z, speed, yaw, mid1, mid2))

    def enable_mission_pads(self):
        return self.send_control_command("mon")

    def disable_mission_pads(self):
        return self.send_control_command("moff")

    def set_mission_pad_detection_direction(self, x):
        return self.send_control_command("mdirection " + str(x))

    def set_speed(self, x: int):
        """Set speed to x cm/s.
        Arguments:
            x: 10-100

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("speed " + str(x))

    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int,
                        yaw_velocity: int):
        """Send RC control via four channels. Command is sent every self.TIME_BTW_RC_CONTROL_COMMANDS seconds.
        Arguments:
            left_right_velocity: -100~100 (left/right)
            forward_backward_velocity: -100~100 (forward/backward)
            up_down_velocity: -100~100 (up/down)
            yaw_velocity: -100~100 (yaw)
        Returns:
            bool: True for successful, False for unsuccessful
        """
        if time.time() - self.last_rc_control_timestamp > self.TIME_BTW_RC_CONTROL_COMMANDS:
            self.last_rc_control_timestamp = time.time()
            return self.send_command_without_return('rc %s %s %s %s' % (self.round_to_100(left_right_velocity),
                                                                        self.round_to_100(forward_backward_velocity),
                                                                        self.round_to_100(up_down_velocity),
                                                                        self.round_to_100(yaw_velocity)))

    def round_to_100(self, x: int):
        if x > 100:
            return 100
        elif x < -100:
            return -100
        else:
            return x

    def set_wifi_credentials(self, ssid, password):
        """Set the Wi-Fi SSID and password. The Tello will reboot afterwords.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command('wifi %s %s' % (ssid, password))

    def connect_to_wifi(self, ssid, password):
        """Connects to the Wi-Fi with SSID and password.
        After this command the tello will reboot
        Only works on Tello EDU
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command('ap %s %s' % (ssid, password))

    def get_speed(self) -> int:
        """Query speed setting (cm/s)
        Returns:
            False: Unsuccessful
            int: 1-100
        """
        return self.send_read_command('speed?')

    def query_battery(self) -> int:
        """Get current battery percentage via a query command
        Using get_battery is usually faster
        Returns:
            False: Unsuccessful
            int: 0-100
        """
        return self.send_read_command('battery?')

    def get_flight_time(self) -> int:
        """Query current fly time (s)
        Returns:
            False: Unsuccessful
            int: Seconds elapsed during flight.
        """
        return self.send_read_command('time?')

    def query_height(self) -> int:
        """Get height in cm via a query command
        Using get_height is usually faster
        Returns:
            False: Unsuccessful
            int: 0-3000
        """
        return self.send_read_command('height?')

    def get_temperature(self) -> int:
        """Query temperature (°C)
        Returns:
            False: Unsuccessful
            int: 0-90
        """
        return self.send_read_command('temp?')

    def get_attitude(self) -> dict:
        """Query IMU attitude data
        Returns:
            False: Unsuccessful
            {'pitch': int, 'roll': int, 'yaw': int}
        """
        r = self.send_read_command('attitude?').replace(';', ':').split(':')
        return dict(zip(r[::2], [int(i) for i in r[1::2]]))  # {'pitch': xxx, 'roll': xxx, 'yaw': xxx}

    def get_barometer(self) -> int:
        """Get barometer value (m)
        Returns:
            False: Unsuccessful
            int: 0-100
        """
        return self.send_read_command('baro?')

    def get_distance_tof(self) -> int:
        """Get distance value from TOF (cm)
        Returns:
            False: Unsuccessful
            int: 30-1000
        """
        return self.send_read_command('tof?')

    def get_wifi(self) -> str:
        """Get Wi-Fi SNR
        Returns:
            False: Unsuccessful
            str: snr
        """
        return self.send_read_command('wifi?')

    def get_sdk_version(self) -> str:
        """Get SDK Version
        Returns:
            False: Unsuccessful
            str: SDK Version
        """
        return self.send_read_command('sdk?')

    def get_serial_number(self) -> str:
        """Get Serial Number
        Returns:
            False: Unsuccessful
            str: Serial Number
        """
        return self.send_read_command('sn?')

    def end(self):
        """Call this method when you want to end the tello object"""
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
    This class read frames from a VideoCapture in background. Then, just call backgroundFrameRead.frame to get the
    actual one.
    """

    def __init__(self, tello, address):
        tello.cap = cv2.VideoCapture(address)
        self.cap = tello.cap

        if not self.cap.isOpened():
            self.cap.open(address)

        self.grabbed, self.frame = self.cap.read()
        self.stopped = False

    def start(self):
        Thread(target=self.update_frame, args=()).start()
        return self

    def update_frame(self):
        while not self.stopped:
            if not self.grabbed or not self.cap.isOpened():
                self.stop()
            else:
                (self.grabbed, self.frame) = self.cap.read()

    def stop(self):
        self.stopped = True
