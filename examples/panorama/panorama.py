from djitellopy import Tello
import cv2
import time
import panoramaModuled


tello = Tello()
tello.connect()

print(tello.get_battery())

tello.takeoff()
tello.move_up(500)
panoramaModuled.panorama_half_clockwise(tello)
tello.land()
