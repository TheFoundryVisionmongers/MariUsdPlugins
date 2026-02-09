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

#include "pxrMariUsdReaderPlugin.h"

#include "UsdReader.h"
#include "CameraAdapter.h"

#include "pxr/base/tf/stringUtils.h"
#include <boost/shared_ptr.hpp>
#include <cstring>
#include <string>
#include <time.h>
#include <sstream>

PXR_NAMESPACE_USING_DIRECTIVE

namespace
{
    MriGeoReaderPluginV1 pluginSuite =
    {
        &load,
        &getSettings,
        &supportedFormats
    };

    MriCameraReaderPluginV2 cameraPluginSuite =
    {
        &loadCamera,
        &supportedFormatsCamera,
        &frameRangeCamera
    };

    PluginHosts pluginHosts;
}

//-----------------------------------------------------------------------------
// Plug-in function suite definitions
//-----------------------------------------------------------------------------

std::string sUsdLog;
std::string sCameraLog;

MriGeoPluginResult load(MriGeoEntityHandle Entity, 
        const char *pFileName, 
        const char **ppMessagesOut)
{
    
    boost::shared_ptr<UsdReader> reader;

    // Check the extension
    if((!TfStringEndsWith(pFileName, ".usd")) &&
       (!TfStringEndsWith(pFileName, ".usda")) &&
       (!TfStringEndsWith(pFileName, ".usdc")) &&
       (!TfStringEndsWith(pFileName, ".usdz"))) {
        pluginHosts.geoReaderHost.trace("[UsdPlugin] Unrecognized extension. Failed to getSettings for %s\n", pFileName);
        return MRI_GPR_FAILED;
    }
    // else
    
    pluginHosts.geoReaderHost.trace("[UsdPlugin] Load %s\n", pFileName);
    reader = boost::shared_ptr<UsdReader>(new UsdReader(pFileName, &pluginHosts));
    MriGeoPluginResult res = reader->Load(Entity);
    sUsdLog = reader->GetLog();
    *ppMessagesOut = sUsdLog.c_str();
    return res;
    

}



//------------------------------------------------------------------------------
// Register the supported formats
MriFileFormatDesc *supportedFormats(int *pNumFormatsOut)
{
    static MriFileFormatDesc formats[4] = {
        {"usd", "USD poseCache file (ASCII or binary)."},
        {"usda", "ASCII USD poseCache file."},
        {"usdc", "binary USD poseCache file."},
        {"usdz", "zipped USD poseCache file."}
    };
    *pNumFormatsOut = 4;
    return formats;
}


//------------------------------------------------------------------------------
// Pre-open a USD stage to detect the UV sets and provide parameter options

MriGeoPluginResult getSettings(MriUserItemHandle SettingsHandle, 
        const char *pFileName)
{
    
    pluginHosts.geoReaderHost.trace("[UsdPlugin] getSettings %s\n", pFileName);

    boost::shared_ptr<UsdReader> reader;

    // Check the extension
    if((!TfStringEndsWith(pFileName, ".usd")) &&
       (!TfStringEndsWith(pFileName, ".usda")) &&
       (!TfStringEndsWith(pFileName, ".usdc")) &&
       (!TfStringEndsWith(pFileName, ".usdz"))) {
        pluginHosts.geoReaderHost.trace("[UsdPlugin] Unrecognized extension. Failed to getSettings for %s\n", pFileName);
        return MRI_GPR_FAILED;
    }
    // else
    
    reader = boost::shared_ptr<UsdReader>(new UsdReader(pFileName, &pluginHosts));

    // Load option
    MriAttributeValue LoadValue;
    LoadValue.m_Type = MRI_ATTR_STRING_LIST;
    LoadValue.m_pString = "First Found\nAll Models\nSpecified Models in Model Names";
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Load", &LoadValue);

    // Merge option
    MriAttributeValue MergeValue;
    MergeValue.m_Type = MRI_ATTR_STRING_LIST;
    MergeValue.m_pString = "Merge Models\nKeep Models Separate";
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Merge Type", &MergeValue);

    // Model option
    MriAttributeValue ModelValue;
    ModelValue.m_Type = MRI_ATTR_STRING;
    ModelValue.m_pString = "";
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Model Names", &ModelValue);

    MriGeoPluginResult res = reader->GetSettings(SettingsHandle);

    // Mapping scheme
    MriAttributeValue MappingSchemeValue;
    MappingSchemeValue.m_Type = MRI_ATTR_STRING_LIST;
    MappingSchemeValue.m_pString = UsdReader::kMappingSchemeOptions.c_str();
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Mapping Scheme", &MappingSchemeValue);

    // frame number
    MriAttributeValue FrameNumberValue;
    FrameNumberValue.m_Type = MRI_ATTR_STRING;
    FrameNumberValue.m_pString = "1";
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Frame Numbers", &FrameNumberValue);
    
    // Gprim Names
    MriAttributeValue GprimValue;
    GprimValue.m_Type = MRI_ATTR_STRING;
    GprimValue.m_pString = "";
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Gprim Names", &GprimValue);

    // Variants
    MriAttributeValue variantsValue;
    variantsValue.m_Type = MRI_ATTR_STRING;
    variantsValue.m_pString = "";
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Variants", &variantsValue);

    // Keep centered
    MriAttributeValue KeepCenteredValue;
    KeepCenteredValue.m_Type = MRI_ATTR_BOOL;
    KeepCenteredValue.m_Int = 0;
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Keep Centered", &KeepCenteredValue);

    // Mari y up
    MriAttributeValue ConformToMariY;
    ConformToMariY.m_Type = MRI_ATTR_BOOL;
    ConformToMariY.m_Int = 1;
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Conform to Mari Y as up", &ConformToMariY);

    // Include Invisible
    MriAttributeValue IncludeInvisibleValue;
    IncludeInvisibleValue.m_Type = MRI_ATTR_BOOL;
    IncludeInvisibleValue.m_Int = 0;
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Include Invisible", &IncludeInvisibleValue);

    // Include CreateFaceSelectionGroups
    MriAttributeValue CreateFaceSelectionGroupsValue;
    CreateFaceSelectionGroupsValue.m_Type = MRI_ATTR_BOOL;
    CreateFaceSelectionGroupsValue.m_Int = 0;
    pluginHosts.geoReaderHost.setAttribute(SettingsHandle, "Create Face Selection Group per mesh", &CreateFaceSelectionGroupsValue);

    return res;
}

//------------------------------------------------------------------------------
// Plug-in interface function definitions
//------------------------------------------------------------------------------

const void *getPluginSuite()
{
    return &pluginSuite;
}

//------------------------------------------------------------------------------

void flushPluginSuite()
{
}

//------------------------------------------------------------------------------

FnPluginStatus setHost(const FnPluginHost* fnPluginHost)
{
    if (fnPluginHost == NULL)
        return FnPluginStatusError;
    
    pluginHosts.pFnPluginHost = fnPluginHost;
    const void* pHostSuite = pluginHosts.pFnPluginHost->getSuite(MRI_GEO_READER_API_NAME, MRI_GEO_READER_API_VERSION);

    if (pHostSuite == NULL)
        return FnPluginStatusError;
    
    pluginHosts.geoReaderHost = *(MriGeoReaderHost *)pHostSuite;
    pluginHosts.geoReaderHost.trace("[UsdPlugin] Plug-in connected to host '%s' version '%s'" "(%u)", pluginHosts.pFnPluginHost->name, pluginHosts.pFnPluginHost->versionStr, pluginHosts.pFnPluginHost->versionInt);
    return FnPluginStatusOK;
}

//------------------------------------------------------------------------------
// Camera reader plugin functions
//------------------------------------------------------------------------------

namespace
{
    bool isValidUsdCameraExtension(const char* pFileName)
    {
        return TfStringEndsWith(pFileName, ".usd") ||
               TfStringEndsWith(pFileName, ".usda") ||
               TfStringEndsWith(pFileName, ".usdc") ||
               TfStringEndsWith(pFileName, ".usdz");
    }
}

MriCameraPluginResult loadCamera(MriCameraHandle CameraHandle,
        const char *pFileName,
        const char **ppMessagesOut)
{
    // Check the extension
    if (!isValidUsdCameraExtension(pFileName))
    {
        pluginHosts.cameraReaderHost.trace("[UsdCameraPlugin] Unrecognized extension. Failed to load camera from %s\n", pFileName);
        return MRI_CAM_FAILED;
    }

    pluginHosts.cameraReaderHost.trace("[UsdCameraPlugin] Load camera from %s\n", pFileName);

    MriCameraPluginResult result = CameraAdapter::LoadFromFile(CameraHandle, pFileName, &pluginHosts.cameraReaderHost, sCameraLog);
    *ppMessagesOut = sCameraLog.c_str();

    return result;
}

//------------------------------------------------------------------------------

MriFileFormatDesc *supportedFormatsCamera(int *pNumFormatsOut)
{
    static MriFileFormatDesc formats[4] = {
        {"usd", "USD camera file (ASCII or binary)."},
        {"usda", "ASCII USD camera file."},
        {"usdc", "binary USD camera file."},
        {"usdz", "zipped USD camera file."}
    };
    *pNumFormatsOut = 4;
    return formats;
}

//------------------------------------------------------------------------------

MriCameraPluginResult frameRangeCamera(const char *pFileName,
        const char *pTake,
        int *pStartFrameOut,
        int *pEndFrameOut,
        const char **ppMessagesOut)
{
    // Check the extension
    if (!isValidUsdCameraExtension(pFileName))
    {
        pluginHosts.cameraReaderHost.trace("[UsdCameraPlugin] Unrecognized extension. Failed to get frame range from %s\n", pFileName);
        return MRI_CAM_FAILED;
    }

    pluginHosts.cameraReaderHost.trace("[UsdCameraPlugin] Get frame range from %s\n", pFileName);

    MriCameraPluginResult result = CameraAdapter::GetFrameRange(pFileName, pStartFrameOut, pEndFrameOut, sCameraLog);
    *ppMessagesOut = sCameraLog.c_str();

    return result;
}

//------------------------------------------------------------------------------

const void *getCameraPluginSuite()
{
    return &cameraPluginSuite;
}

//------------------------------------------------------------------------------

void flushCameraPluginSuite()
{
}

//------------------------------------------------------------------------------

FnPluginStatus setCameraHost(const FnPluginHost* fnPluginHost)
{
    if (fnPluginHost == NULL)
        return FnPluginStatusError;

    pluginHosts.pFnPluginHost = fnPluginHost;
    const void* pHostSuite = pluginHosts.pFnPluginHost->getSuite(MRI_CAMERA_READER_API_NAME, MRI_CAMERA_READER_API_VERSION);

    if (pHostSuite == NULL)
        return FnPluginStatusError;

    pluginHosts.cameraReaderHost = *(MriCameraReaderHost *)pHostSuite;
    pluginHosts.cameraReaderHost.trace("[UsdCameraPlugin] Camera plug-in connected to host '%s' version '%s'" "(%u)",
        pluginHosts.pFnPluginHost->name, pluginHosts.pFnPluginHost->versionStr, pluginHosts.pFnPluginHost->versionInt);
    return FnPluginStatusOK;
}

//------------------------------------------------------------------------------

extern "C"
{
    FnPlugin *getPlugins(unsigned int *pNumPlugins)
    {
        static FnPlugin s_Plugins[2];

        // Geo Reader Plugin
        s_Plugins[0].name = "USD importer";
        s_Plugins[0].pluginVersionMajor = 1;
        s_Plugins[0].pluginVersionMinor = 0;
        s_Plugins[0].apiName = MRI_GEO_READER_API_NAME;
        s_Plugins[0].apiVersion = 5004;
        s_Plugins[0].setHost = &setHost;
        s_Plugins[0].getSuite = &getPluginSuite;
        s_Plugins[0].flush = &flushPluginSuite;
        
        // Camera Reader Plugin
        s_Plugins[1].name = "USD camera importer";
        s_Plugins[1].pluginVersionMajor = 1;
        s_Plugins[1].pluginVersionMinor = 0;
        s_Plugins[1].apiName = MRI_CAMERA_READER_API_NAME;
        s_Plugins[1].apiVersion = MRI_CAMERA_READER_API_VERSION;
        s_Plugins[1].setHost = &setCameraHost;
        s_Plugins[1].getSuite = &getCameraPluginSuite;
        s_Plugins[1].flush = &flushCameraPluginSuite;
        
        *pNumPlugins = 2;
        return s_Plugins;
    }
}
