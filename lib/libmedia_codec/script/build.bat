cd %~dp0/..
del /s /q build
del /s /q dist
del /s /q output
del /s /q robomaster_media_decoder.egg-info
rmdir /s /q build
rmdir /s /q dist
rmdir /s /q output
rmdir /s /q robomaster_media_decoder.egg-info
python setup.py build
python setup.py bdist_wheel
