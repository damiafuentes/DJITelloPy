from djitellopy import Tello
import cv2
import datetime as dt
import numpy as np
import threading
import os

import pygame
import pygame.font

from time import sleep
from time import time as now


MOVEMENT_SPEED = 100


class Drone(threading.Thread):
    def __init__(self):
        super(Drone, self).__init__()

        self.tello = Tello()

        self.starting_barometer = 0
        self.camera_feed = None
        self.terminate = False
        self.is_ready = False

    def takeoff(self):
        self.starting_barometer = self.tello.get_barometer()
        self.tello.takeoff()

    def land(self):
        self.tello.land()

    def is_flying(self):
        return self.tello.is_flying

    def stop(self):
        self.terminate = True
        self.is_ready = False
        if self.tello.is_flying:
            print("Drone is currently in-flight: Forcing to land.")
            self.tello.land()

    def get_altitude(self):
        return self.tello.get_barometer() - self.starting_barometer

    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int, yaw_velocity: int):
        self.tello.send_rc_control(left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity)

    def run(self):
        try:
            self.tello.connect()

            sleep(1)
            print("Drone connected")

            self.tello.streamon()
            sleep(1)
            print("Drone now streaming")

            self.camera_feed = self.tello.get_frame_read()
            self.starting_barometer = self.tello.get_barometer()

            print("Drone ready to receive commands")
            self.is_ready = True

            while not self.terminate:
                sleep(0.01)
        except:
            self.terminate = True
            raise


class Interface:
    def __init__(self):
        pygame.init()
        pygame.display.init()
        pygame.font.init()

        self.surface = pygame.display.set_mode([1280, 720])
        pygame.display.set_caption("COMMAND & CONTROL")

        self.font = pygame.font.SysFont("dejavusansmono", 24)
        self.hud_elements = []

        self.last_rc_command = (0, 0, 0, 0)
        self.last_image_taken = now()
        self.terminate = False
        self.video = None

        if not os.path.isdir("images"):
            os.mkdir("images")

        if not os.path.isdir("videos"):
            os.mkdir("videos")

    def grab_frame(self):
        return self.drone.camera_feed.frame

    def run(self):
        self.drone = Drone()
        self.drone.daemon = True
        self.drone.start()

        while not self.drone.is_ready:
            sleep(0.001)
            if self.drone.terminate:
                return

        threading.Thread(target=self.capture_controls).start()

        steps = 0
        while not self.terminate:
            steps += 1
            if steps % 15 == 1:
                self.hud_elements = [
                    (f"Battery:  {self.drone.tello.get_battery():.0f}%"),
                    (f"Altitude: {self.drone.get_altitude():.1f}cm"),
                    (f"Flight:   {self.drone.tello.get_flight_time():.0f}s"),
                    (f""),
                    (f"Accel X:  {self.drone.tello.get_acceleration_x():.0f}"),
                    (f"Accel Y:  {self.drone.tello.get_acceleration_y():.0f}"),
                    (f"Accel Z:  {self.drone.tello.get_acceleration_z():.0f}"),
                    (f""),
                    (f"Roll:     {self.drone.tello.get_roll():.1f}"),
                    (f"Pitch:    {self.drone.tello.get_pitch():.1f}"),
                    (f"Yaw:      {self.drone.tello.get_yaw():.1f}"),
                ]

            f = self.grab_frame()
            if f is not None:
                if self.video is None:
                    height, width, _ = f.shape
                    self.video = cv2.VideoWriter(
                        f"videos/{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}.avi", cv2.VideoWriter_fourcc(*"XVID"), 30, (width, height)
                    )

                video_f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
                self.video.write(video_f)

                self.update_display(f)

            sleep(1 / 30)

    def update_display(self, frame):
        self.surface.fill([0, 0, 0])

        if frame is not None:
            frame = np.fliplr(frame)
            frame = np.rot90(frame)
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            surf = pygame.surfarray.make_surface(frame)
            self.surface.blit(surf, (0, 0))

        color = (0, 255, 0)
        (w, h) = (300, 20)
        blits = []
        for element in self.hud_elements:
            add = self.font.render(element, True, color)
            blits += [(add, (0, h))]
            h += add.get_height()

        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0))
        for blit in blits:
            overlay.blit(*blit)

        self.surface.blit(overlay, (1280 - w - 2, 0))
        pygame.display.update()

    def capture_controls(self):
        def get_key(key):
            for event in pygame.event.get():
                pass

            pressed_keys = pygame.key.get_pressed()
            target_key = getattr(pygame, f"K_{key}")
            out = pressed_keys[target_key]
            return out

        while True:
            sleep(0.001)

            if get_key("ESCAPE"):
                self.drone.stop()
                self.terminate = True
                print("Terminated")
                return

            lr, fb, ud, yv = (0, 0, 0, 0)
            if get_key("LEFT"):
                lr -= MOVEMENT_SPEED
            elif get_key("RIGHT"):
                lr += MOVEMENT_SPEED

            if get_key("UP"):
                fb += MOVEMENT_SPEED
            elif get_key("DOWN"):
                fb -= MOVEMENT_SPEED

            if get_key("w"):
                ud += MOVEMENT_SPEED
            elif get_key("s"):
                ud -= MOVEMENT_SPEED

            if get_key("a"):
                yv -= MOVEMENT_SPEED
            elif get_key("d"):
                yv += MOVEMENT_SPEED

            rc_command = (lr, fb, ud, yv)

            if rc_command != (0, 0, 0, 0) or self.last_rc_command != (0, 0, 0, 0):
                self.last_rc_command = rc_command
                self.drone.send_rc_control(*rc_command)

            if get_key("t"):
                self.drone.takeoff()
            elif get_key("l"):
                self.drone.land()

            if get_key("e") and now() - self.last_image_taken > 0.5:
                print("Taking screenshot")
                cv2.imwrite(f"images/{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}.jpg", self.latest_image)
                self.last_image_taken = now()


if __name__ == "__main__":
    interface = Interface()
    interface.run()
