#Simply import of "panoramaModule.py" and you can use each function by calling it with name of the drone inside arguments.
from djitellopy import Tello
import cv2
import time
import panoramaModule


tello = Tello()
tello.connect()

print(tello.get_battery())

tello.takeoff()
tello.move_up(500)
panoramaModule.panorama_half_clockwise(tello)
tello.land()
