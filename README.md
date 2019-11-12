# DJITelloPy
DJI Tello drone python interface using the official [Tello SDK](https://dl-cdn.ryzerobotics.com/downloads/tello/20180910/Tello%20SDK%20Documentation%20EN_1.3.pdf) and [Tello EDU SDK](https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf). Yes, this library has been tested with the drone. 
Please see [example.py](https://github.com/damiafuentes/TelloSDKPy/blob/master/example.py) for a working example controlling the drone as a remote controller with the keyboard and the video stream in a window.  

Tested with Python 3.6, but it also may be compatabile with other versions.

## Install through git clone
```
$ pip install --upgrade pip
$ git clone https://github.com/damiafuentes/TelloSDKPy.git
$ cd TelloSDKPy
$ pip install -r requirements.txt
```
Sometimes you need to update the virtual environment indexes and skeletons in order for the `example.py` file to work with `pygame. If you are working with PyCharm, this can be done to ```File > Invalidate Caches```

## Install through pip
NOTICE: The python package at PyPi library is hardly every maintained. I would recommend to install it through ``git clone``.
```
$ pip install djitellopy
```

## Usage

### Simple example

```python
from TelloSDKPy.djitellopy import Tello
import cv2
import time

tello = Tello()

tello.connect()
tello.takeoff()

tello.move_left(100)
tello.rotate_counter_clockwise(45)

tello.land()
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

### Swarm example
Only for Tello EDU's.
```python
from TelloSDKPy.djitellopy import TelloSwarm

swarm = TelloSwarm.fromIps([
    "192.168.178.42",
    "192.168.178.43",
    "192.168.178.44"
])

swarm.connect()
swarm.takeoff()

# run in parallel on all tellos
swarm.move_up(100)

# run by one tello after the other
swarm.sequential(lambda i, tello: tello.move_forward(i * 20))

# making each tello do something unique in parallel
swarm.parallel(lambda i, tello: tello.move_left(i * 100))

swarm.land()
swarm.end()
```

### Notes
- If you are using the ```streamon``` command and the response is ```Unknown command``` means you have to update the Tello firmware. That can be done through the Tello app.
- Mission pad detection and navigation is only supported by the Tello EDU.
- Connecting to an existing wifi network is only supported by the Tello EDU.
- When connected to an existing wifi network video streaming is not available.

## Author

* **Damià Fuentes Escoté** 

## License

This project is licensed under the MIT License - see the [LICENSE.md](https://github.com/damiafuentes/TelloSDKPy/blob/master/LICENSE) file for details

