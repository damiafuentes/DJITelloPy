from tello import Tello
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
            if not tello.takeoff():
                print("%s, Not taken off" % (time.time() - start_time))
        if ch == ord('l'):
            if not tello.land():
                print("%s, Not landed" % (time.time() - start_time))
        if ch == 27:
            frame_read.stopped = True
            break

    tello.end()


start()
