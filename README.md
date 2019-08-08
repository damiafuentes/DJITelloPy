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
$ pip install -r requirements.txt
```

## Usage

### Simple example

```python
from djitellopy import Tello
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

### Swarm example
```python
from djitellopy import TelloSwarm

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

### Example using pygame and the video stream
Please see [example.py](https://github.com/damiafuentes/TelloSDKPy/blob/master/example.py). 

The controls are:
- T: Takeoff
- L: Land
- Arrow keys: Forward, backward, left and right.
- A and D: Counter clockwise and clockwise rotations
- W and S: Up and down.

### Notes
- If you are using the ```streamon``` command and the response is ```Unknown command``` means you have to update the Tello firmware. That can be done through the Tello app.
- Mission pad detection and navigation is only supported by the Tello EDU
- Connecting to an existing wifi network is only supported by the Tello EDU
- When connected to an existing wifi network video streaming is not available

## Author

* **Damià Fuentes Escoté** 


## License

This project is licensed under the MIT License - see the [LICENSE.md](https://github.com/damiafuentes/TelloSDKPy/blob/master/LICENSE) file for details

