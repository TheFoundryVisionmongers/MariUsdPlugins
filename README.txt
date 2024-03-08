Introduction
------------
This repository contains the Mari USD CAPI plugins, which facilitate basic
importing of USD scene graph data.

The plug-in code was originally authored by Pixar as a proof-of-concept.
In 2019, Foundry and Pixar agreed Foundry should maintain and curate
the plug-ins, and so the plug-ins were made available under the same
Modified Apache 2.0 license as the main USD library.

This file will guide you through building the Mari USD CAPI plugin.
The capi plugin code can be found on github at
https://github.com/TheFoundryVisionmongers/mariusdplugins

For information about USD, please visit https://graphics.pixar.com/usd/docs/index.html.


Dependencies
------------
The following dependencies are required:
 - C++ 17 compiler
 - [CMake](https://cmake.org/documentation/) (3.11 onwards)
 - [Boost](https://boost.org) (1.76.0 onwards)
 - [Intel TBB](https://www.threadingbuildingblocks.org/) (2020U3 onwards)
 - [Ninja](https://ninja-build.org/) (1.10.2 onwards)
 - [Usd](https://github.com/PixarAnimationStudios/USD) (22.05)

The following dependencies are optional:
 - [Python](https://python.org) (3.9 onwards)


Required environment variables
------------------------------
We're using CMake to configure our project, with Ninja as the generator. The latter is chosen because it is cross-platform and works out of the box on both Linux and Windows.
The code requires a C++17 compiler and we've tested it with GCC 9.3.1 on Linux and Visual Studio 2019 on Windows.

The following paths are required and need to be set as environment variables:
- USD_ROOT : path to the USD libraries
    - At this location, we need "include", lib" and "pxrConfig.cmake"
- TBB_DIR : path to TBB libraries
    - At this location, we need "include", "lib" and "cmake/TBBConfig.cmake"
- BOOST_ROOT : path to Boost directory
- BOOST_INCLUDEDIR : path to Boost include directory
- BOOST_LIBRARYDIR : path to Boost lib directory
    - We are assuming that Boost is built as static libraries. If that is not the case, please update the CMakeListx.txt file to: set (Boost_USE_STATIC_LIBS OFF)
- MARI_SDK_INCLUDE_DIR : path to Mari SDK include directory. These are the required CAPI header files.
- PYTHON_ROOT : path to Python libraries. This is optional and set, the build will look and link python libraries to the plugin.


Example on Linux in Bash:
export USD_ROOT=/tmp/USD
export TBB_DIR=/tmp/TBB
export BOOST_ROOT=/tmp/Boost
export BOOST_INCLUDEDIR=/tmp/Boost/include
export BOOST_LIBRARYDIR=/tmp/Boost/lib
export MARI_SDK_INCLUDE_DIR=/tmp/Mari6.0v1/SDK/include
export PYTHON_ROOT=/tmp/Python

Example on Windows 10 in VS2019 x64 Native Tools Command Prompt:
set USD_ROOT=C:/Build/usd
set TBB_DIR=C:/Build/tbb
set BOOST_ROOT=C:/Build/Boost
set BOOST_INCLUDEDIR=C:/Build/Boost/include
set BOOST_LIBRARYDIR=C:/Build/Boost/lib
set MARI_SDK_INCLUDE_DIR=C:/Installation/Mari6.0v1/Bundle/SDK/include


Building the Code
-----------------
Note : CMake uses a temporary path as install directory. Please specify where to install the plugin by passing -DCMAKE_INSTALL_PREFIX=<path_to_install>


1. To build the project, create a build directory and call "cmake" on the CMakeLists.txt file and use "Ninja" as generator.
(Assuming you checked out the plugin from git at /tmp/UsdPlugin)
- cd /tmp/UsdPlugin
- mkdir buildplugin
- cd buildplugin

(Linux)
- cmake -G Ninja -D CMAKE_MAKE_PROGRAM:FILEPATH=/tmp/Ninja/1.10.2/bin/ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/tmp/MyPlugin ../

(Windows)
- cmake.exe -G Ninja -D CMAKE_MAKE_PROGRAM:FILEPATH=C:\Installation\Ninja\1.10.2\bin\ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=C:\MyPlugin ..\


2. This should create a ninja project for us. Then run "ninja" to compile and install:

(Linux)
- /tmp/Ninja/1.10.2/bin/ninja install

(Windows)
- C:\Installation\Ninja\1.10.2\bin\ninja.exe install

The plugin will be built as libUSDImport.so on Linux and USDImport.dll on Windows. A "lib" folder will also be created which contains all the required libraries to make the plugin run.


Running the Code
----------------
1. Copy the plugin (libUSDImport.so on Linux and USDImport.dll on Windows) to your Mari "Plugins" folder.
This will normally be "~/Mari/Plugins" on Linux and "C:\users\<username>\Documents\Mari\Plugins" on Window.

2. We then need to point Mari to the "lib" folder so the usd plugin loads.

(Linux, assuming the "lib" folder is found at /tmp/MyPlugin/lib)
export ROOT=/tmp/MyPlugin
export PATH=$ROOT/lib/:$PATH
export LD_LIBRARY_PATH=$ROOT/lib/:$LD_LIBRARY_PATH
export PYTHONPATH=$ROOT/lib/python/:$PYTHONPATH

(Windows, assuming the "lib" folder is found at C:\MyPlugin\lib)
- Update the environment registry PATH to C:\MyPlugin\lib
- Update the environment registry PYTHONPATH to C:\MyPlugin\lib\python

