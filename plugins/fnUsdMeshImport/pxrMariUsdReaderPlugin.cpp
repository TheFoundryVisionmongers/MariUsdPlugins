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

#include "pxr/base/tf/stringUtils.h"
#include <boost/shared_ptr.hpp>
#include <string>
#include <time.h>
#include <sstream>

using namespace std;
PXR_NAMESPACE_USING_DIRECTIVE

//-----------------------------------------------------------------------------
// Plug-in function suite definitions
//-----------------------------------------------------------------------------

std::string sUsdLog;

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
        host.trace("[UsdPlugin] Unrecognized extension. Failed to getSettings for %s\n", pFileName);
        return MRI_GPR_FAILED;
    }
    // else
    
    host.trace("[UsdPlugin] Load %s\n", pFileName);
    reader = boost::shared_ptr<UsdReader>(new UsdReader(pFileName, 
                                                        host));
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
    
    host.trace("[UsdPlugin] getSettings %s\n", pFileName);

    boost::shared_ptr<UsdReader> reader;

    // Check the extension
    if((!TfStringEndsWith(pFileName, ".usd")) &&
       (!TfStringEndsWith(pFileName, ".usda")) &&
       (!TfStringEndsWith(pFileName, ".usdc")) &&
       (!TfStringEndsWith(pFileName, ".usdz"))) {
        host.trace("[UsdPlugin] Unrecognized extension. Failed to getSettings for %s\n", pFileName);
        return MRI_GPR_FAILED;
    }
    // else
    
    reader = boost::shared_ptr<UsdReader>(new UsdReader(pFileName, 
                                                        host));

    // Load option
    MriAttributeValue LoadValue;
    LoadValue.m_Type = MRI_ATTR_STRING_LIST;
    LoadValue.m_pString = "First Found\nAll Models\nSpecified Models in Model Names";
    host.setAttribute(SettingsHandle,
        "Load",
        &LoadValue);

    // Merge option
    MriAttributeValue MergeValue;
    MergeValue.m_Type = MRI_ATTR_STRING_LIST;
    MergeValue.m_pString = "Merge Models\nKeep Models Separate";
    host.setAttribute(SettingsHandle,
        "Merge Type",
        &MergeValue);

    // Model option
    MriAttributeValue ModelValue;
    ModelValue.m_Type = MRI_ATTR_STRING;
    ModelValue.m_pString = "";
    host.setAttribute(SettingsHandle,
        "Model Names",
        &ModelValue);

    MriGeoPluginResult res = reader->GetSettings(SettingsHandle);

    // Mapping scheme
    MriAttributeValue MappingSchemeValue;
    MappingSchemeValue.m_Type = MRI_ATTR_STRING_LIST;
    MappingSchemeValue.m_pString = "UV if available, Ptex otherwise\nForce Ptex";
    host.setAttribute(SettingsHandle, "Mapping Scheme", &MappingSchemeValue);

    // frame number
    MriAttributeValue FrameNumberValue;
    FrameNumberValue.m_Type = MRI_ATTR_STRING;
    FrameNumberValue.m_pString = "1";
    host.setAttribute(SettingsHandle, "Frame Numbers", &FrameNumberValue);
    
    // Gprim Names
    MriAttributeValue GprimValue;
    GprimValue.m_Type = MRI_ATTR_STRING;
    GprimValue.m_pString = "";
    host.setAttribute(SettingsHandle,
        "Gprim Names",
        &GprimValue);

    // Variants
    MriAttributeValue variantsValue;
    variantsValue.m_Type = MRI_ATTR_STRING;
    variantsValue.m_pString = "";
    host.setAttribute(SettingsHandle,
        "Variants",
        &variantsValue);

    // Keep centered
    MriAttributeValue KeepCenteredValue;
    KeepCenteredValue.m_Type = MRI_ATTR_BOOL;
    KeepCenteredValue.m_Int = 0;
    host.setAttribute(SettingsHandle, "Keep Centered", &KeepCenteredValue);

    // Mari y up
    MriAttributeValue ConformToMariY;
    ConformToMariY.m_Type = MRI_ATTR_BOOL;
    ConformToMariY.m_Int = 1;
    host.setAttribute(SettingsHandle, "Conform to Mari Y as up", &ConformToMariY);

    // Include Invisible
    MriAttributeValue IncludeInvisibleValue;
    IncludeInvisibleValue.m_Type = MRI_ATTR_BOOL;
    IncludeInvisibleValue.m_Int = 0;
    host.setAttribute(SettingsHandle, "Include Invisible", &IncludeInvisibleValue);

    // Include CreateFaceSelectionGroups
    MriAttributeValue CreateFaceSelectionGroupsValue;
    CreateFaceSelectionGroupsValue.m_Type = MRI_ATTR_BOOL;
    CreateFaceSelectionGroupsValue.m_Int = 0;
    host.setAttribute(SettingsHandle, "Create Face Selection Group per mesh", &CreateFaceSelectionGroupsValue);

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

FnPluginStatus setHost(const FnPluginHost *pHost)
{
    const void *pHostSuite = NULL;
    
    if (pHost == NULL)
        return FnPluginStatusError;
    
    pHostSuite = pHost->getSuite(MRI_GEO_READER_API_NAME, 
#if MARI_VERSION < 30
            MRI_GEO_READER_API_VERSION);
#else
            4006);
#endif

    if (pHostSuite == NULL)
        return FnPluginStatusError;
    
    host = *(MriGeoReaderHost *)pHostSuite;

    host.trace("[UsdPlugin] Plug-in connected to host '%s' version '%s'"
            "(%u)", pHost->name, pHost->versionStr, pHost->versionInt);
    return FnPluginStatusOK;
}

//------------------------------------------------------------------------------

extern "C"
{
    FnPlugin *getPlugins(unsigned int *pNumPlugins)
    {
        static FnPlugin s_Plugin;
        
        s_Plugin.name = "Usd importer";
        s_Plugin.pluginVersionMajor = 1;
        s_Plugin.pluginVersionMinor = 0;
        s_Plugin.apiName = MRI_GEO_READER_API_NAME;
        s_Plugin.apiVersion = 4006;
        s_Plugin.setHost = &setHost;
        s_Plugin.getSuite = &getPluginSuite;
        s_Plugin.flush = &flushPluginSuite;
        
        *pNumPlugins = 1;
        return &s_Plugin;
    }
}
