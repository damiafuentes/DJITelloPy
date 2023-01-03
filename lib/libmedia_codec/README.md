# cmake_example for pybind11

[![Build Status](https://travis-ci.org/pybind/cmake_example.svg?branch=master)](https://travis-ci.org/pybind/cmake_example)
[![Build status](https://ci.appveyor.com/api/projects/status/57nnxfm4subeug43/branch/master?svg=true)](https://ci.appveyor.com/project/dean0x7d/cmake-example/branch/master)

An example [pybind11](https://github.com/pybind/pybind11) module built with a
CMake-based build system. This is useful for C++ codebases that have an existing
CMake project structure.


## Prerequisites

**On Unix (Linux, OS X)**

* A compiler with C++11 support
* CMake >= 2.8.12

**On Windows**

* Visual Studio 2015 (required for all Python versions, see notes below)
* CMake >= 3.1


## Installation

Just clone this repository and pip install. Note the `--recursive` option which is
needed for the pybind11 submodule:

```bash
git clone --recursive https://github.com/pybind/cmake_example.git
pip install ./cmake_example
```

With the `setup.py` file included in this example, the `pip install` command will
invoke CMake and build the pybind11 module as specified in `CMakeLists.txt`.


## Special notes for Windows

**Compiler requirements**

Pybind11 requires a C++11 compliant compiler, i.e Visual Studio 2015 on Windows.
This applies to all Python versions, including 2.7. Unlike regular C extension
modules, it's perfectly fine to compile a pybind11 module with a VS version newer
than the target Python's VS version. See the [FAQ] for more details.

**Runtime requirements**

The Visual C++ 2015 redistributable packages are a runtime requirement for this
project. It can be found [here][vs2015_runtime]. If you use the Anaconda Python
distribution, you can add `vs2015_runtime` as a platform-dependent runtime
requirement for you package: see the `conda.recipe/meta.yaml` file in this example.


## Building the documentation

Documentation for the example project is generated using Sphinx. Sphinx has the
ability to automatically inspect the signatures and documentation strings in
the extension module to generate beautiful documentation in a variety formats.
The following command generates HTML-based reference documentation; for other
formats please refer to the Sphinx manual:

 - `cd cmake_example/docs`
 - `make html`


## License

Pybind11 is provided under a BSD-style license that can be found in the LICENSE
file. By using, distributing, or contributing to this project, you agree to the
terms and conditions of this license.


## Test call

```python
import cmake_example
cmake_example.add(1, 2)
```


[FAQ]: http://pybind11.rtfd.io/en/latest/faq.html#working-with-ancient-visual-studio-2009-builds-on-windows
[vs2015_runtime]: https://www.microsoft.com/en-us/download/details.aspx?id=48145
