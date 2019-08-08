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

# TODO: need to find a better way to specify the Mari SDK
target_include_directories(
    USDImport
    PRIVATE
    D:/dev/Mari4.1/Apps/Mari/objects/win-64-x86-release-14.0.24210-dynamic/Bundle/SDK/include
)

target_compile_options(
    USDImport
    PRIVATE
    -DMARI_VERSION=41
    -DBOOST_CONFIG_SUPPRESS_OUTDATED_MESSAGE
    $<$<CXX_COMPILER_ID:MSVC>:-WX -W4 -DNOMINMAX -DWIN32_LEAN_AND_MEAN /FIiso646.h -wd4244 -wd4305 -wd4800 -wd4100 -wd4267 -wd4018 -wd4996 -wd4701>
)

target_link_libraries(
    USDImport
    PRIVATE
    usdGeom
)

install(
    TARGETS
    USDImport
    DESTINATION
    ${CMAKE_INSTALL_PREFIX}
)

# TODO: these need to go beside the main executable, not the plugin
#FILE(GLOB USD_dlls "${USD_ROOT}/lib/*.dll")
#install(
#    FILES
#    ${USD_dlls}
#    $<$<CONFIG:Debug>:${TBB_DIR}/../lib/tbb_debug.dll>
#    $<$<CONFIG:Release>:${TBB_DIR}/../lib/tbb.dll>
#    DESTINATION
#    ${CMAKE_INSTALL_PREFIX}
#)
