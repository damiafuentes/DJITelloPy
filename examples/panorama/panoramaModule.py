#Module with individual panorama types defined. You can just import it and use hovever you like
#
#It will save photos from Tello inside folder that's in. You can change this by changing path inside every function.
from djitellopy import Tello
import cv2
import time

global img


def panorama_full_clockwise(tello_name):
    tello = tello_name
    tello.streamoff()
    tello.streamon()

    for i in range(4):
        img = tello.get_frame_read().frame
        cv2.imwrite(f'Panorama-full-clockwise_{time.time()}.jpg', img)
        time.sleep(1)
        tello.rotate_clockwise(80)

    img = tello.get_frame_read().frame
    cv2.imwrite(f'Panorama-full-clockwise_{time.time()}.jpg', img)
    time.sleep(1)
    tello.rotate_clockwise(40)

    tello.streamoff()


def panorama_half_clockwise(tello_name):
    tello = tello_name
    tello.streamoff()
    tello.streamon()

    tello.rotate_counter_clockwise(90)

    for i in range(3):
        img = tello.get_frame_read().frame
        cv2.imwrite(f'Panorama-half-clockwise_{time.time()}.jpg', img)
        time.sleep(1)
        tello.rotate_clockwise(60)

    img = tello.get_frame_read().frame
    cv2.imwrite(f'Panorama-half-clockwise_{time.time()}.jpg', img)
    time.sleep(1)
    tello.rotate_counter_clockwise(90)

    tello.streamoff()


def panorama_full_counter_clockwise(tello_name):
    tello = tello_name
    tello.streamoff()
    tello.streamon()

    for i in range(4):
        img = tello.get_frame_read().frame
        cv2.imwrite(f'Panorama-full-counter-clockwise_{time.time()}.jpg', img)
        time.sleep(1)
        tello.rotate_counter_clockwise(80)

    img = tello.get_frame_read().frame
    cv2.imwrite(f'/Panorama-full-counter-clockwise_{time.time()}.jpg', img)
    time.sleep(1)
    tello.rotate_counter_clockwise(40)

    tello.streamoff()


def panorama_half_counter_clockwise(tello_name):
    tello = tello_name
    tello.streamoff()
    tello.streamon()

    tello.rotate_clockwise(90)

    for i in range(3):
        img = tello.get_frame_read().frame
        cv2.imwrite(f'Panorama-half-counter-clockwise_{time.time()}.jpg', img)
        time.sleep(1)
        tello.rotate_counter_clockwise(60)

    img = tello.get_frame_read().frame
    cv2.imwrite(f'Panorama_half_counter_clockwise-{time.time()}.jpg', img)
    time.sleep(1)
    tello.rotate_clockwise(90)

    tello.streamoff()
