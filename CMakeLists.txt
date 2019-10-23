cmake_minimum_required(VERSION 3.11)

project(
    mariUsdImport
    VERSION 1.0
    DESCRIPTION "Mari USD Import"
    LANGUAGES CXX
)

# Set essential dependencies
if (WIN32)
    if (${CMAKE_BUILD_TYPE} STREQUAL "Debug")
        set (BUILD_TYPE "debug")
    else()
        set (BUILD_TYPE "release")
    endif()

    set (USD_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../Thirdparty/USD/19.05/win/${BUILD_TYPE}/usd")
    set (TBB_DIR "${CMAKE_CURRENT_LIST_DIR}/../../Thirdparty/USD/19.05/win/${BUILD_TYPE}/tbb/cmake")
    set (BOOST_INCLUDEDIR "${CMAKE_CURRENT_LIST_DIR}/../../Thirdparty/Boost/1.61.0/bin/include")
    set (BOOST_LIBRARYDIR "${CMAKE_CURRENT_LIST_DIR}/../../Thirdparty/Boost/1.61.0/bin/win-64-x86-${BUILD_TYPE}-14.0.24210-dynamic/lib")

    # Include for Mari CAPI SDK
    set (MARI_SDK_INCLUDE_DIR D:/Working/Mari4.6/test_release/FnBundle/Bundle/SDK/include)
else()
    set (USD_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../Thirdparty/USD/19.05/linux/release/usd")
    set (TBB_DIR "${CMAKE_CURRENT_LIST_DIR}/../../Thirdparty/USD/19.05/linux/release/tbb/cmake")
    set (BOOST_INCLUDEDIR "${CMAKE_CURRENT_LIST_DIR}/../../Thirdparty/Boost/1.61.0/bin/include")
    set (BOOST_LIBRARYDIR "${CMAKE_CURRENT_LIST_DIR}/../../Thirdparty/Boost/1.61.0/bin/win-64-x86-debug-14.0.24210-dynamic/lib")

    # Include for Mari CAPI SDK
    set (MARI_SDK_INCLUDE_DIR /home/rajiv/Working/Mari4.7/test_debug/FnBundle/SDK/include)
endif()

message(STATUS "USD_ROOT: ${USD_ROOT}")
message(STATUS "TBB_DIR: ${TBB_DIR}")
message(STATUS "BOOST_INCLUDEDIR: ${BOOST_INCLUDEDIR}")
message(STATUS "BOOST_LIBRARYDIR: ${BOOST_LIBRARYDIR}")

# Set cmake install path
set (CMAKE_INSTALL_PREFIX "${CMAKE_BINARY_DIR}/build" CACHE PATH "Bundling output path" FORCE)
file (MAKE_DIRECTORY ${CMAKE_INSTALL_PREFIX})
message(STATUS "CMAKE_INSTALL_PREFIX: ${CMAKE_INSTALL_PREFIX}")

# Use C++ 11
set (CMAKE_CXX_STANDARD "11" CACHE STRING "" FORCE)
set (CMAKE_CXX_STANDARD_REQUIRED ON CACHE BOOL "" FORCE)
set (CMAKE_CXX_EXTENSIONS OFF CACHE BOOL "" FORCE)

include(${USD_ROOT}/pxrConfig.cmake)
find_package(TBB CONFIG REQUIRED)
find_package(Boost REQUIRED)

add_library(
    USDImport
    SHARED
    ${CMAKE_CURRENT_LIST_DIR}/GeoData.cpp
    ${CMAKE_CURRENT_LIST_DIR}/ModelData.cpp
    ${CMAKE_CURRENT_LIST_DIR}/pxrMariUsdReaderPlugin.cpp
    ${CMAKE_CURRENT_LIST_DIR}/UsdReader.cpp
    ${CMAKE_CURRENT_LIST_DIR}/GeoData.h
    ${CMAKE_CURRENT_LIST_DIR}/ModelData.h
    ${CMAKE_CURRENT_LIST_DIR}/pxrMariUsdReaderPlugin.h
    ${CMAKE_CURRENT_LIST_DIR}/UsdReader.h
    ${CMAKE_CURRENT_LIST_DIR}/MariHostConfig.h
)

target_include_directories(
    USDImport
    PRIVATE
    ${MARI_SDK_INCLUDE_DIR}
)

target_compile_options(
    USDImport
    PRIVATE
    -DMARI_VERSION=46
    -DBOOST_CONFIG_SUPPRESS_OUTDATED_MESSAGE
    $<$<CXX_COMPILER_ID:MSVC>:-WX -W4 -DNOMINMAX -DWIN32_LEAN_AND_MEAN /FIiso646.h -wd4244 -wd4305 -wd4800 -wd4100 -wd4267 -wd4018 -wd4996 -wd4701>
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
if (WIN32)
    FILE(GLOB USD_dlls "${USD_ROOT}/lib/*.dll")
    FILE(GLOB TBB_dlls "${TBB_DIR}/../lib/*.dll")
else()
    FILE(GLOB USD_dlls "${USD_ROOT}/lib/*.so")
    FILE(GLOB TBB_dlls "${TBB_DIR}/../lib/*.so*")
endif()
install(
    FILES
    ${USD_dlls}
    ${TBB_dlls}
    DESTINATION
    ${CMAKE_INSTALL_PREFIX}/lib
)
install(
    DIRECTORY
    ${USD_ROOT}/lib/usd
    DESTINATION
    ${CMAKE_INSTALL_PREFIX}/lib
)