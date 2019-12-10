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

#include "MriGeoReaderPlugin.h"

#include <assert.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string>

#include "MariHostConfig.h"

/// Returns the list of plug-ins in this library
extern "C"
#ifdef _WIN32
__declspec(dllexport)
#else
__attribute__((visibility("default")))
#endif
FnPlugin *getPlugins(unsigned int *pNumPlugins);


/// Loads a geometry file
MriGeoPluginResult load(MriGeoEntityHandle Entity, 
        const char *pFileName, 
        const char **ppMessagesOut);
/// Retrieves the settings for loading a geometry file
MriGeoPluginResult getSettings(MriUserItemHandle SettingsHandle, 
        const char *pFileName);
/// Returns the formats supported by the plug-in
MriFileFormatDesc *supportedFormats(int *pNumFormatsOut);


/// Sets the host information for a plug-in
FnPluginStatus setHost(const FnPluginHost *pHost);
/// Returns the suite of functions provided by a plug-in
const void *getPluginSuite();
/// Cleans up the plug-in
void flushPluginSuite();

///< The host structure, which contains functions that the plug-in can call
MriGeoReaderHost host;

/// The plug-in structure, to provide to the host so it can call functions 
/// when needed
MriGeoReaderPluginV1 pluginSuite =
{
    &load,
    &getSettings,
    &supportedFormats
};
