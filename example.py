from TelloSDKPy.tello import Tello
import time
import cv2


def start():
    start_time = time.time()

    tello = Tello()

    if not tello.connect():
        print("%s, Not connected" % (time.time() - start_time))
        return

    if not tello.streamon():
        print("%s, Could not start video stream" % (time.time() - start_time))
        return

    frame_read = tello.get_frame_read()

    while True:
        if frame_read.stopped:
            frame_read.stop()
            break

        cv2.imshow('Augmented reality', frame_read.frame)

        ch = cv2.waitKey(1)
        if ch == ord('t'):
            tello.takeoff()
        if ch == ord('l'):
            tello.land()
        if ch == ord('a'):
            tello.move_left(20)
        if ch == ord('d'):
            tello.move_right(20)
        if ch == ord('w'):
            tello.move_forward(20)
        if ch == ord('d'):
            tello.move_back(20)
        if ch == ord('e'):
            tello.rotate_counter_clockwise(450)
        if ch == ord('r'):
            tello.rotate_clockwise(450)
        if ch == ord('f'):
            tello.move_up(20)
        if ch == ord('g'):
            tello.move_down(20)
        if ch == 27:
            frame_read.stopped = True
            break

    tello.end()


start()
