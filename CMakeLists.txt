cmake_minimum_required(VERSION 3.11)

project(mariUsdImport)

# Get essential dependencies
if (NOT DEFINED ENV{USD_ROOT})
    message(FATAL_ERROR "USD_ROOT has not been set")
else()
    message(STATUS "USD_ROOT: $ENV{USD_ROOT}")
endif()
if (NOT DEFINED ENV{TBB_DIR})
    message(FATAL_ERROR "TBB_DIR has not been set")
else()
    message(STATUS "TBB_DIR: $ENV{TBB_DIR}")
endif()
if (NOT DEFINED ENV{BOOST_ROOT})
    message(FATAL_ERROR "BOOST_ROOT has not been set")
else()
    message(STATUS "BOOST_ROOT: $ENV{BOOST_ROOT}")
endif()
if (NOT DEFINED ENV{BOOST_INCLUDEDIR})
    message(FATAL_ERROR "BOOST_INCLUDEDIR has not been set")
else()
    message(STATUS "BOOST_INCLUDEDIR: $ENV{BOOST_INCLUDEDIR}")
endif()
if (NOT DEFINED ENV{BOOST_LIBRARYDIR})
    message(FATAL_ERROR "BOOST_LIBRARYDIR has not been set")
else()
    message(STATUS "BOOST_LIBRARYDIR: $ENV{BOOST_LIBRARYDIR}")
endif()
if (NOT DEFINED ENV{MARI_SDK_INCLUDE_DIR})
    message(FATAL_ERROR "MARI_SDK_INCLUDE_DIR has not been set")
else()
    message(STATUS "MARI_SDK_INCLUDE_DIR: $ENV{MARI_SDK_INCLUDE_DIR}")
endif()

include($ENV{USD_ROOT}/pxrConfig.cmake)
find_package(TBB CONFIG REQUIRED)

if (NOT DEFINED ENV{PYTHON_ROOT})
    message(STATUS "Python not enabled")
else()
    message(STATUS "Adding python package with PYTHON_ROOT: $ENV{PYTHON_ROOT}")
    set (Python_DIR "$ENV{PYTHON_ROOT}/cmake")
    find_package(Python CONFIG REQUIRED)
endif()

if (NOT DEFINED Boost_USE_STATIC_LIBS)
    set (Boost_USE_STATIC_LIBS ON)
    message(STATUS "Setting Boost_USE_STATIC_LIBS to ${Boost_USE_STATIC_LIBS}")
else()
    message(STATUS "Boost_USE_STATIC_LIBS: ${Boost_USE_STATIC_LIBS}")
endif()
find_package(Boost COMPONENTS python)

message(STATUS "CMAKE_INSTALL_PREFIX: ${CMAKE_INSTALL_PREFIX}")

# Use C++ 14
set (CMAKE_CXX_STANDARD "14" CACHE STRING "" FORCE)
set (CMAKE_CXX_STANDARD_REQUIRED ON CACHE BOOL "" FORCE)
set (CMAKE_CXX_EXTENSIONS OFF CACHE BOOL "" FORCE)

add_library(
    USDImport
    SHARED
    ${CMAKE_CURRENT_LIST_DIR}/plugins/fnUsdMeshImport/GeoData.cpp
    ${CMAKE_CURRENT_LIST_DIR}/plugins/fnUsdMeshImport/ModelData.cpp
    ${CMAKE_CURRENT_LIST_DIR}/plugins/fnUsdMeshImport/pxrMariUsdReaderPlugin.cpp
    ${CMAKE_CURRENT_LIST_DIR}/plugins/fnUsdMeshImport/UsdReader.cpp
    ${CMAKE_CURRENT_LIST_DIR}/plugins/fnUsdMeshImport/GeoData.h
    ${CMAKE_CURRENT_LIST_DIR}/plugins/fnUsdMeshImport/ModelData.h
    ${CMAKE_CURRENT_LIST_DIR}/plugins/fnUsdMeshImport/pxrMariUsdReaderPlugin.h
    ${CMAKE_CURRENT_LIST_DIR}/plugins/fnUsdMeshImport/UsdReader.h
    ${CMAKE_CURRENT_LIST_DIR}/plugins/fnUsdMeshImport/MariHostConfig.h
)

target_include_directories(
    USDImport
    PRIVATE
    $ENV{MARI_SDK_INCLUDE_DIR}
)

target_compile_options(
    USDImport
    PRIVATE
    -DMARI_VERSION=50
    -DBOOST_CONFIG_SUPPRESS_OUTDATED_MESSAGE
    $<$<CONFIG:Debug>:-DBOOST_DEBUG_PYTHON>
    $<$<CXX_COMPILER_ID:MSVC>:-WX -W4 -DNOMINMAX -DWIN32_LEAN_AND_MEAN /FIiso646.h -wd4201 -wd4127 -wd4244 -wd4305 -wd4800 -wd4100 -wd4267 -wd4018 -wd4996 -wd4701 -EHsc>
    $<$<CXX_COMPILER_ID:GNU>:-Wall -Werror -Wno-sign-compare -Wno-deprecated>
)

target_link_libraries(
    USDImport
    PRIVATE
    usdGeom
)

# Bundling
install(
    TARGETS
    USDImport
    DESTINATION
    ${CMAKE_INSTALL_PREFIX}
)
# Copy across libs
install(
    DIRECTORY
    $ENV{USD_ROOT}/lib
    DESTINATION
    ${CMAKE_INSTALL_PREFIX}
)
install(
    DIRECTORY
    $ENV{TBB_DIR}/lib
    DESTINATION
    ${CMAKE_INSTALL_PREFIX}
)
install(
    DIRECTORY
    $ENV{BOOST_LIBRARYDIR}
    DESTINATION
    ${CMAKE_INSTALL_PREFIX}
)
if (DEFINED ENV{PYTHON_ROOT})
    install(
        DIRECTORY
        $ENV{PYTHON_ROOT}/lib
        DESTINATION
        ${CMAKE_INSTALL_PREFIX}
    )
endif()
# Copy across bin dlls for windows
FILE(GLOB LibFiles "$ENV{USD_ROOT}/bin/*.dll")
list(APPEND DEP_LIB_FILES ${LibFiles})
FILE(GLOB LibFiles "$ENV{TBB_DIR}/bin/*.dll")
list(APPEND DEP_LIB_FILES ${LibFiles})
FILE(GLOB LibFiles "$ENV{BOOST_ROOT}/bin/*.dll")
list(APPEND DEP_LIB_FILES ${LibFiles})
install(
    FILES
    ${DEP_LIB_FILES}
    DESTINATION
    ${CMAKE_INSTALL_PREFIX}/lib
)
