# DJITelloPy
DJI Tello drone python interface using the official [Tello SDK](https://dl-cdn.ryzerobotics.com/downloads/tello/20180910/Tello%20SDK%20Documentation%20EN_1.3.pdf) and [Tello EDU SDK](https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf). This library has the following features:

- implementation of all tello commands
- easily retrieve a video stream
- receive and parse state packets
- control a swarm of drones
- support for python >= 3.6

Feel free to contribute!

## Install using pip
```
$ pip install https://github.com/damiafuentes/DJITelloPy/archive/master.zip
```

For Linux distributions with both python2 and python3 (e.g. Debian, Ubuntu, ...) you need to run
```
$ pip3 install https://github.com/damiafuentes/DJITelloPy/archive/master.zip
```

## Install using git clone
```
$ pip install --upgrade pip
$ git clone https://github.com/damiafuentes/TelloSDKPy.git
$ cd TelloSDKPy
$ pip install -r requirements.txt
```

### Install in developer mode
Run the following command from the root directory that contains the file `setup.py` to install `djitellopy` from its working directory in developer mode.

It is recommended to install this package in a virtual environment. Check [Virtual Environments and Packages Tutorial](https://docs.python.org/3/tutorial/venv.html) 
to learn how to create and activate a Python virtual environment.

```
$ pip install -e .
```

The `-e` option will install the package in _editable_ or _developer_ mode so every time you make a change it will be included in the package automatically.

## Usage

### API Reference

See [djitellopy.readthedocs.io](https://djitellopy.readthedocs.io/en/latest/) for a full reference of all classes and methods available.

### Simple example

```python
from djitellopy import Tello

tello = Tello()

tello.connect()
tello.takeoff()

tello.move_left(100)
tello.rotate_counter_clockwise(90)
tello.move_forward(100)

tello.land()
```

### More examples
In the [examples](examples/) directory there are some code examples:

- [taking a picture](examples/take-picture.py)
- [recording a video](examples/record-video.py)
- [flying a swarm (multiple tellos at once)](examples/simple-swarm.py)
- [simple controlling using your keyboard](examples/manual-control-opencv.py)
- [fully featured manual control using pygame](examples/manual-control-pygame.py)

### Notes
- If you are using the ```streamon``` command and the response is ```Unknown command``` means you have to update the Tello firmware. That can be done through the Tello app.
- Mission pad detection and navigation is only supported by the Tello EDU.
- Connecting to an existing wifi network is only supported by the Tello EDU.
- When connected to an existing wifi network video streaming is not available.

## Authors

* **Damià Fuentes Escoté**
* **Jakob Löw**
* [and more](https://github.com/damiafuentes/DJITelloPy/graphs/contributors)

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details

