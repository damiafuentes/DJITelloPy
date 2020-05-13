from djitellopy import Tello
import cv2, math, time

tello = Tello()
tello.connect()

tello.streamoff()
time.sleep(1)
tello.streamon()

cv2.namedWindow("drone")
frame_read = tello.get_frame_read()

try:
    while True:
        img = frame_read.frame
        cv2.imshow("drone", img)

        key = cv2.waitKey(1) & 0xff
        if key == ord('t'):
            tello.takeoff()
        elif key == ord('l'):
            tello.land()
        elif key == ord('w'):
            tello.move_forward(30)
        elif key == ord('s'):
            tello.move_down(30)
        elif key == ord('a'):
            tello.move_left(30)
        elif key == ord('d'):
            tello.move_right(30)
        elif key == ord('e'):
            tello.rotate_clockwise(30)
        elif key == ord('q'):
            tello.rotate_counter_clockwise(30)
        elif key == ord('r'):
            tello.move_up(30)
        elif key == ord('f'):
            tello.move_down(30)

except KeyboardInterrupt:
    tello.end()
