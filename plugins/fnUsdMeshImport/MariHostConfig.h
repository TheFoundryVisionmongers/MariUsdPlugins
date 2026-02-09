#ifndef MARI_HOST_CONFIG_H
#define MARI_HOST_CONFIG_H

// These files were initially authored by Pixar.
// In 2019, Foundry and Pixar agreed Foundry should maintain and curate
// these plug-ins, and they moved to
// https://github.com/TheFoundryVisionmongers/mariusdplugins
// under the same Modified Apache 2.0 license as the main USD library,
// as shown below.
//
// Copyright 2019 Pixar
//
// Licensed under the Apache License, Version 2.0 (the "Apache License")
// with the following modification; you may not use this file except in
// compliance with the Apache License and the following modification to it:
// Section 6. Trademarks. is deleted and replaced with:
//
// 6. Trademarks. This License does not grant permission to use the trade
//    names, trademarks, service marks, or product names of the Licensor
//    and its affiliates, except as required to comply with Section 4(c) of
//    the License and to reproduce the content of the NOTICE file.
//
// You may obtain a copy of the Apache License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the Apache License with the above modification is
// distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied. See the Apache License for the specific
// language governing permissions and limitations under the Apache License.
//

#include <MriGeoReaderPlugin.h>
#include <MriCameraReaderPlugin.h>

#if MARI_VERSION < 30
typedef MriGeoReaderHostV2  MriGeoReaderHost;
#else
typedef MriGeoReaderHostV7  MriGeoReaderHost;
#endif

typedef MriCameraReaderHostV1  MriCameraReaderHost;

/// Holds all the hosts available to this plugin.
struct PluginHosts
{
    const FnPluginHost* pFnPluginHost;      ///< The Foundry Plugin Host.
    MriGeoReaderHost    geoReaderHost;      ///< The geometry host structure, which contains functions that the plug-in can call
    MriCameraReaderHost cameraReaderHost;   ///< The camera host structure, which contains functions for camera loading
};

#endif // MARI_HOST_CONFIG_H
