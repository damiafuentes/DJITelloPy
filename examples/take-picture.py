import cv2
from djitellopy import Tello

tello = Tello()
tello.connect()

tello.streamon()
frame_read = tello.get_frame_read()

# Wait for video frames before doing other things
while True:
    if frame_read.frame is not None:
        break
    time.sleep(1)

tello.takeoff()
cv2.imwrite("picture.png", frame_read.frame)

tello.land()
