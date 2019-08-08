#include "MriGeoReaderPlugin.h"

#include <assert.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string>

#include "MariHostConfig.h"

/// Returns the list of plug-ins in this library
extern "C" FnPlugin *getPlugins(unsigned int *pNumPlugins);


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
