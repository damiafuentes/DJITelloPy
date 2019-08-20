# coding=utf-8
import logging
import socket
import time
import threading
import cv2
from threading import Thread
from djitellopy.decorators import accepts


class Tello:
    """Python wrapper to interact with the Ryze Tello drone using the official Tello api.
    Tello API documentation:
    https://dl-cdn.ryzerobotics.com/downloads/tello/20180910/Tello%20SDK%20Documentation%20EN_1.3.pdf
    """
    # Send and receive commands, client socket
    UDP_IP = '192.168.10.1'
    UDP_PORT = 8889
    RESPONSE_TIMEOUT = 7  # in seconds
    TIME_BTW_COMMANDS = 1  # in seconds
    TIME_BTW_RC_CONTROL_COMMANDS = 0.5  # in seconds
    RETRY_COUNT = 3
    last_received_command = time.time()

    HANDLER = logging.StreamHandler()
    FORMATTER = logging.Formatter('%(message)s')
    HANDLER.setFormatter(FORMATTER)

    LOGGER = logging.getLogger('djitellopy')
    LOGGER.addHandler(HANDLER)
    LOGGER.setLevel(logging.INFO)
    # use logging.getLogger('djitellopy').setLevel(logging.<LEVEL>) in YOUR CODE
    # to only receive logs of the desired level and higher

    # Video stream, server socket
    VS_UDP_IP = '0.0.0.0'
    VS_UDP_PORT = 11111

    STATE_UDP_PORT = 8890

    # VideoCapture object
    cap = None
    background_frame_read = None

    stream_on = False

    def __init__(self,
        host='192.168.10.1',
        port=8889,
        client_socket=None,
        enable_exceptions=True,
        retry_count=3):

        self.address = (host, port)
        self.response = None
        self.response_state = None  #to attain the response of the states
        self.stream_on = False
        self.enable_exceptions = enable_exceptions
        self.retry_count = retry_count

        if client_socket:
            self.clientSocket = client_socket
        else:
            self.clientSocket = socket.socket(socket.AF_INET,  # Internet
                                            socket.SOCK_DGRAM)  # UDP
            self.clientSocket.bind(('', self.UDP_PORT))  # For UDP response (receiving data)

        self.stateSocket = socket.socket(socket.AF_INET,
                                          socket.SOCK_DGRAM)
        self.stateSocket.bind(('', self.STATE_UDP_PORT))# for accessing the states of Tello

        # Run tello udp receiver on background
        thread1 = threading.Thread(target=self.run_udp_receiver, args=())
        # Run state reciever on background
        thread2 = threading.Thread(target=self.get_states, args=())

        thread1.daemon = True
        thread2.daemon = True
        thread1.start()
        thread2.start()

    def run_udp_receiver(self):
        """Setup drone UDP receiver. This method listens for responses of Tello. Must be run from a background thread
        in order to not block the main thread."""
        while True:
            try:
                self.response, _ = self.clientSocket.recvfrom(256)  # buffer size is 1024 bytes
            except Exception as e:
                self.LOGGER.error(e)
                break

    def get_states(self):
        """This runs on background to recieve the state of Tello"""
        while True:
            try:
                self.response_state, _ = self.stateSocket.recvfrom(128)
            except Exception as e:
                self.LOGGER.error(e)
                break

    def get_current_state_all(self):
        """Call this function to attain the states of Tello"""
        if self.response_state == 'ok':
            return False
            # print(self.response_state)
            # print(self.response_state.decode('ASCII'))
        else:
            try:
                return self.response_state.decode('ASCII')
            except:
                print("Exception in getting initial state only")
                return 0

    def get_pitch(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[1])
            except:
                print("Exception in pitch occured")
                return 0

    def get_roll(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[3])
            except:
                print("Exception in roll occured")
                return 0

    def get_yaw(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[5])
            except:
                print("Exception in yaw occured")
                return 0

    def get_vgx(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[7])
            except:
                print("Exception in velocity in x occured")
                return 0

    def get_vgy(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[9])
            except:
                print("Exception in velocity in y occured")
                return 0

    def get_vgz(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[11])
            except:
                print("Exception in velocity in z occured")
                return 0

    def get_agx(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[27])
            except:
                print("Exception in acceleration in x")
                return 0

    def get_agy(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[29])
            except:
                print("Exception in acceleration in y")
                return 0

    def get_agz(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[31])
            except:
                print("Exception in acceleration in z")
                return 0

    def get_h(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[19])
            except:
                print("Exception in height")
                return 0

    def get_bat(self):
        if self.response_state == 'ok':
            return False
        else:
            try:
                response = self.get_current_state_all()
                response = response.replace(';',':')
                response = response.split(':')
                return float(response[21])
            except:
                print("Exception in battery")
                return 0

    def get_udp_video_address(self):
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

    def get_frame_read(self):
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

    @accepts(command=str)
    def send_command_with_return(self, command):
        """Send command to Tello and wait for its response.
        Return:
            bool: True for successful, False for unsuccessful
        """
        # Commands very consecutive makes the drone not respond to them. So wait at least self.TIME_BTW_COMMANDS seconds
        diff = time.time() * 1000 - self.last_received_command
        if diff < self.TIME_BTW_COMMANDS:
            time.sleep(diff)

        self.LOGGER.info('Send command: ' + command)
        timestamp = int(time.time() * 1000)

        self.clientSocket.sendto(command.encode('utf-8'), self.address)

        while self.response is None:
            if (time.time() * 1000) - timestamp > self.RESPONSE_TIMEOUT * 1000:
                self.LOGGER.warning('Timeout exceed on command ' + command)
                return False

        response = self.response.decode('utf-8').rstrip("\r\n")

        self.LOGGER.info('Response: ' + response)

        self.response = None

        self.last_received_command = time.time() * 1000

        return response

    @accepts(command=str)
    def send_command_without_return(self, command):
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
        self.clientSocket.sendto(command.encode('utf-8'), self.address)

    @accepts(command=str)
    def send_control_command(self, command):
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

        for i in range(0, self.retry_count):
            response = self.send_command_with_return(command)

            if response == 'OK' or response == 'ok':
                return True

        return self.return_error_on_send_command(command, response, self.enable_exceptions)

    @accepts(command=str)
    def send_read_command(self, command):
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
            bool: True for successful, False for unsuccessful
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
                return response
        else:
            return self.return_error_on_send_command(command, response, self.enable_exceptions)

    @staticmethod
    def return_error_on_send_command(command, response, enable_exceptions):
        """Returns False and print an informative result code to show unsuccessful response"""
        msg = 'Command ' + command + ' was unsuccessful. Message: ' + str(response)
        if enable_exceptions:
            raise Exception(msg)
        else:
            self.LOGGER.error(msg)
            return False


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
        return self.send_control_command("takeoff")

    def land(self):
        """Tello auto land
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("land")

    def streamon(self):
        """Set video stream on. If the response is 'Unknown command' means you have to update the Tello firmware. That
        can be done through the Tello app.
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

    @accepts(direction=str, x=int)
    def move(self, direction, x):
        """Tello fly up, down, left, right, forward or back with distance x cm.
        Arguments:
            direction: up, down, left, right, forward or back
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command(direction + ' ' + str(x))

    @accepts(x=int)
    def move_up(self, x):
        """Tello fly up with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("up", x)

    @accepts(x=int)
    def move_down(self, x):
        """Tello fly down with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("down", x)

    @accepts(x=int)
    def move_left(self, x):
        """Tello fly left with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("left", x)

    @accepts(x=int)
    def move_right(self, x):
        """Tello fly right with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("right", x)

    @accepts(x=int)
    def move_forward(self, x):
        """Tello fly forward with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("forward", x)

    @accepts(x=int)
    def move_back(self, x):
        """Tello fly back with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("back", x)

    @accepts(x=int)
    def move_up(self, x):
        """Tello fly up with distance x cm.
        Arguments:
            x: 20-500

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("up", x)

    @accepts(x=int)
    def rotate_clockwise(self, x):
        """Tello rotate x degree clockwise.
        Arguments:
            x: 1-360

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("cw " + str(x))

    @accepts(x=int)
    def rotate_counter_clockwise(self, x):
        """Tello rotate x degree counter-clockwise.
        Arguments:
            x: 1-3600

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("ccw " + str(x))

    @accepts(x=str)
    def flip(self, direction):
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

    @accepts(x=int, y=int, z=int, speed=int)
    def go_xyz_speed(self, x, y, z, speed):
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

    @accepts(x1=int, y1=int, z1=int, x2=int, y2=int, z2=int, speed=int)
    def curve_xyz_speed(self, x1, y1, z1, x2, y2, z2, speed):
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

    @accepts(x=int, y=int, z=int, speed=int, mid=int)
    def go_xyz_speed_mid(self, x, y, z, speed, mid):
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

    @accepts(x1=int, y1=int, z1=int, x2=int, y2=int, z2=int, speed=int, mid=int)
    def curve_xyz_speed_mid(self, x1, y1, z1, x2, y2, z2, speed, mid):
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

    @accepts(x=int, y=int, z=int, speed=int, yaw=int, mid1=int, mid2=int)
    def go_xyz_speed_yaw_mid(self, x, y, z, speed, yaw, mid1, mid2):
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

    @accepts(x=int)
    def set_speed(self, x):
        """Set speed to x cm/s.
        Arguments:
            x: 10-100

        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("speed " + str(x))

    last_rc_control_sent = 0

    @accepts(left_right_velocity=int, forward_backward_velocity=int, up_down_velocity=int, yaw_velocity=int)
    def send_rc_control(self, left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity):
        """Send RC control via four channels. Command is sent every self.TIME_BTW_RC_CONTROL_COMMANDS seconds.
        Arguments:
            left_right_velocity: -100~100 (left/right)
            forward_backward_velocity: -100~100 (forward/backward)
            up_down_velocity: -100~100 (up/down)
            yaw_velocity: -100~100 (yaw)
        Returns:
            bool: True for successful, False for unsuccessful
        """
        if int(time.time() * 1000) - self.last_rc_control_sent < self.TIME_BTW_RC_CONTROL_COMMANDS:
            pass
        else:
            self.last_rc_control_sent = int(time.time() * 1000)
            return self.send_command_without_return('rc %s %s %s %s' % (left_right_velocity, forward_backward_velocity,
                                                                        up_down_velocity, yaw_velocity))

    def set_wifi_credentials(self, ssid, password):
        """Set the Wi-Fi SSID and password. The Tello will reboot afterwords.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command('wifi %s %s' % (ssid, password))

    def connect_to_wifi(self, ssid, password):
        """Connects to the Wi-Fi with SSID and password.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command('ap %s %s' % (ssid, password))

    def get_speed(self):
        """Get current speed (cm/s)
        Returns:
            False: Unsuccessful
            int: 1-100
        """
        return self.send_read_command('speed?')

    def get_battery(self):
        """Get current battery percentage
        Returns:
            False: Unsuccessful
            int: -100
        """
        return self.send_read_command('battery?')

    def get_flight_time(self):
        """Get current fly time (s)
        Returns:
            False: Unsuccessful
            int: Seconds elapsed during flight.
        """
        return self.send_read_command('time?')

    def get_height(self):
        """Get height (cm)
        Returns:
            False: Unsuccessful
            int: 0-3000
        """
        return self.send_read_command('height?')

    def get_temperature(self):
        """Get temperature (°C)
        Returns:
            False: Unsuccessful
            int: 0-90
        """
        return self.send_read_command('temp?')

    def get_attitude(self):
        """Get IMU attitude data
        Returns:
            False: Unsuccessful
            int: pitch roll yaw
        """
        return self.send_read_command('attitude?')

    def get_barometer(self):
        """Get barometer value (m)
        Returns:
            False: Unsuccessful
            int: 0-100
        """
        return self.send_read_command('baro?')

    def get_distance_tof(self):
        """Get distance value from TOF (cm)
        Returns:
            False: Unsuccessful
            int: 30-1000
        """
        return self.send_read_command('tof?')

    def get_wifi(self):
        """Get Wi-Fi SNR
        Returns:
            False: Unsuccessful
            str: snr
        """
        return self.send_read_command('wifi?')

    def get_sdk_version(self):
        """Get SDK Version
        Returns:
            False: Unsuccessful
            str: SDK Version
        """
        return self.send_read_command('sdk?')

    def get_serial_number(self):
        """Get Serial Number
        Returns:
            False: Unsuccessful
            str: Serial Number
        """
        return self.send_read_command('sn?')

    def end(self):
        """Call this method when you want to end the tello object"""
        if self.stream_on:
            self.streamoff()
        if self.background_frame_read is not None:
            self.background_frame_read.stop()
        if self.cap is not None:
            self.cap.release()


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