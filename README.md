# TelloSDKPy
DJI Tello drone python interface using the official [Tello SDK](https://dl-cdn.ryzerobotics.com/downloads/tello/20180910/Tello%20SDK%20Documentation%20EN_1.3.pdf). This library has been tested.

## Prerequisites

You will need python-opencv and threading packages:

```
pip install python-opencv
pip install threading
```

## Usage
```
git clone https://github.com/damiafuentes/TelloSDKPy.git
```

```
from TelloSDKPy.tello import Tello
import cv2


tello = Tello()

tello.connect()

tello.set_speed(10)

tello.streamon()

frame_read = tello.get_frame_read()

while True:
    if frame_read.stopped:
        frame_read.stop()
        break

    cv2.imshow('Augmented reality', frame_read.frame)

    ccv2.waitKey(1)
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
```

Note: If you are using the streamon command and the response is 'Unknown command' means you have to update the Tello firmware. That can be done through the Tello app.

## Author

* **Damià Fuentes Escoté** 


## License

This project is licensed under the MIT License - see the [LICENSE.md](https://github.com/damiafuentes/TelloSDKPy/blob/master/LICENSE) file for details

