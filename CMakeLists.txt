# Note: macOS untested due to failing Mari builds of the 4.6 branches
cmake_minimum_required(VERSION 3.13)

project(
    mariUsdImport
    VERSION 1.0
    DESCRIPTION "Mari USD Import"
    LANGUAGES CXX
)

if(NOT USD_ROOT)
    message(FATAL_ERROR "USD_ROOT has not been specified")
endif()

if(WIN32)
    file(TO_CMAKE_PATH "${USD_ROOT}" USD_ROOT)
endif()

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

if (MARI_BUILD)
    set(MARI_SDK_INCLUDE_DIR ${CMAKE_SOURCE_DIR}/src/MriCAPI/include)
else()
    # TODO: change this for the local build on your machine
    set(MARI_SDK_INCLUDE_DIR D:/dev/Mari4.1/Apps/Mari/objects/win-64-x86-release-14.0.24210-dynamic/Bundle/SDK/include)
endif()
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

if (MARI_BUILD)
    if (WIN32)
        install(
            TARGETS
            USDImport
            DESTINATION
            ${CMAKE_INSTALL_PREFIX}/Bundle/capiplugins
        )
        FILE(GLOB USD_dlls "${USD_ROOT}/lib/*.dll")
        FILE(GLOB TBB_dlls "${TBB_DIR}/../lib/*.dll")
        install(
            FILES
            ${USD_dlls}
            $<$<CONFIG:Debug>:${TBB_DIR}/../lib/tbb_debug.dll>
            $<$<CONFIG:Release>:${TBB_DIR}/../lib/tbb.dll>
            DESTINATION
            ${CMAKE_INSTALL_PREFIX}/Bundle/bin
        )
        install(
            DIRECTORY
            ${USD_ROOT}/lib/usd
            DESTINATION
            ${CMAKE_INSTALL_PREFIX}/Bundle/bin
        )
    elseif(UNIX AND NOT APPLE)
        install(
            TARGETS
            USDImport
            DESTINATION
            ${CMAKE_INSTALL_PREFIX}/capiplugins
        )
        FILE(GLOB USD_dlls "${USD_ROOT}/lib/*.so")
        FILE(GLOB TBB_dlls "${TBB_DIR}/../lib/*.so*")
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
    else()
        install(
            TARGETS
            USDImport
            DESTINATION
            ${CMAKE_INSTALL_PREFIX}/capiplugins
        )
        FILE(GLOB USD_dlls "${USD_ROOT}/lib/*.dylib")
        FILE(GLOB TBB_dlls "${TBB_DIR}/../lib/*.dylib")
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
    endif()
else()
    install(
        TARGETS
        USDImport
        DESTINATION
        ${CMAKE_INSTALL_PREFIX}
    )
endif()
