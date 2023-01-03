import copy
import numpy as np
import time
from threading import Thread
from djitellopy import Tello
import matplotlib.pyplot as plt

class viewer:
    def __init__(self):
        self.cont = False
    def run(self):

        display = None

        while self.cont:
            self.frame = copy.deepcopy(tello.get_latest_video_frame())
            
            print(self.frame)
            print(type(self.frame))
            print(np.shape(self.frame))

            if display is None:
                display = plt.imshow(self.frame)
            else:
                display.set_data(self.frame)
            plt.pause(.1)
            plt.draw()
        
    def startCamera(self):
        self.cont = True

    def stopCamera(self):
        self.cont = False



# Connect to the drone
tello = Tello()
tello.connect()

# Turn on the camera
tello.streamon()

# Get the frame_read object
tello.start_video()

# Turn motors on for cooling
tello.turn_motor_on()

# Create the viewer
v = viewer()

# Start the camera thread
v.startCamera()
a = Thread(target=v.run)
a.start()

# This is where you could do other things...
time.sleep(60)

# Turn motors off
tello.turn_motor_off()

# Stop the camera
v.stopCamera()
a.join