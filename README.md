# TelloSDKPy
DJI Tello drone python interface using the official [Tello SDK](https://dl-cdn.ryzerobotics.com/downloads/tello/20180910/Tello%20SDK%20Documentation%20EN_1.3.pdf). 
Yes, this library has been tested with the drone. 
Please see [example.py](https://github.com/damiafuentes/TelloSDKPy/blob/master/example.py) for a working example controlling the drone as a remote controller with the keyboard and the video stream in a window.  

Tested with Python 3.6, but it also may be compatabile with other versions.

## Install
```
$ pip install djitellopy
```
or
```
$ git clone https://github.com/damiafuentes/TelloSDKPy.git
$ cd DJITelloPy
$ pip install requirements.txt
```

## Usage

### Simple example

```
from djitellopy import Tello
import cv2
import time


tello = Tello()

tello.connect()

tello.takeoff()
time.sleep(5)

tello.move_left(100)
time.sleep(5)

tello.rotate_counter_clockwise(45)
time.sleep(5)

tello.land()
time.sleep(5)
        
tello.end()
```

### Example using pygame and the video stream
Please see [example.py](https://github.com/damiafuentes/TelloSDKPy/blob/master/example.py). 

The controls are:
- T: Takeoff
- L: Land
- Arrow keys: Forward, backward, left and right.
- A and D: Counter clockwise and clockwise rotations
- W and S: Up and down.

### Note
If you are using the ```streamon``` command and the response is ```Unknown command``` means you have to update the Tello firmware. That can be done through the Tello app.

## Author

* **Damià Fuentes Escoté** 


## License

This project is licensed under the MIT License - see the [LICENSE.md](https://github.com/damiafuentes/TelloSDKPy/blob/master/LICENSE) file for details

