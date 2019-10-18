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
    reader->CloseLog();
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

    MriGeoPluginResult res = reader->GetSettings(SettingsHandle);


    // frame number
    MriAttributeValue FrameNumberValue;
    FrameNumberValue.m_Type = MRI_ATTR_STRING;
    FrameNumberValue.m_pString = "1";
    host.setAttribute(SettingsHandle, "frameNumbers", &FrameNumberValue);
    
    // Gprim Names
    MriAttributeValue GprimValue;
    GprimValue.m_Type = MRI_ATTR_STRING;
    GprimValue.m_pString = "";
    host.setAttribute(SettingsHandle,
        "gprimNames", 
        &GprimValue);

    // Variants
    MriAttributeValue variantsValue;
    variantsValue.m_Type = MRI_ATTR_STRING;
    variantsValue.m_pString = "";
    host.setAttribute(SettingsHandle,
        "variants", 
        &variantsValue);

    // Model option 
    MriAttributeValue ModelValue;
    ModelValue.m_Type = MRI_ATTR_STRING;
    ModelValue.m_pString = "_FirstFound";
    host.setAttribute(SettingsHandle,
        "modelName", 
        &ModelValue);

    // Keep centered
    MriAttributeValue KeepCenteredValue;
    KeepCenteredValue.m_Type = MRI_ATTR_BOOL;
    KeepCenteredValue.m_Int = 0;
    host.setAttribute(SettingsHandle, "keepCentered", &KeepCenteredValue);

    // Include Invisible
    MriAttributeValue IncludeInvisibleValue;
    IncludeInvisibleValue.m_Type = MRI_ATTR_BOOL;
    IncludeInvisibleValue.m_Int = 0;
    host.setAttribute(SettingsHandle, "includeInvisible", &IncludeInvisibleValue);

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
            3000);
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
        s_Plugin.apiVersion = MRI_GEO_READER_API_VERSION;
        s_Plugin.setHost = &setHost;
        s_Plugin.getSuite = &getPluginSuite;
        s_Plugin.flush = &flushPluginSuite;
        
        *pNumPlugins = 1;
        return &s_Plugin;
    }
}
