#ifndef USD_READER_H
#define USD_READER_H

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
#include "GeoData.h"
#include "ModelData.h"
#include "pxr/usd/usd/stage.h"
#include "pxr/usd/usd/prim.h"
#include "pxr/usd/usd/variantSets.h"

/// This macro provides a very simple result code check
#define CHECK_RESULT(expr)  { \
                                Result = expr; \
                                if (Result != MRI_GPR_SUCCEEDED) \
                                    return Result; \
                            }


/// UsdReader base class.
class UsdReader
{
    public:

        UsdReader(const char* pFileName, MriGeoReaderHost &pHost);

        std::string GetLog();

        
        MriGeoPluginResult Load(MriGeoEntityHandle &pEntity);
        MriGeoPluginResult GetSettings(MriUserItemHandle SettingsHandle);


    protected:
        MriGeoPluginResult _MakeGeoEntity(GeoData &Geom, 
                MriGeoEntityHandle &Entity, 
                std::string label, 
                const std::vector<int> &frames,
                bool createFaceSelectionGroups);
        
        static void _GetFrameList(const std::string &frameString, 
                std::vector<int> &frames);

        static void _GetVariantSelectionsList(const std::string &variantsString, 
                std::vector<PXR_NS::SdfPath> &variants);

        static FILE * _GetMetadataFile();
        static FILE * _GetLogFile();
        void _ParseUVs(MriUserItemHandle SettingsHandle, 
                GeoData::UVSet uvs, int size);
        
        void _GetMariAttributes(MriGeoEntityHandle &Entity,
                std::string& loadOption,
                std::string& mergeOption,
                std::vector<int>& frames,
                std::string& frameString,
                std::vector<std::string>& requestedModelNames,
                std::vector<std::string>& requestedGprimNames,
                std::string& UVSet,
                std::vector<PXR_NS::SdfPath>& variantSelections,
                bool &conformToMariY,
                bool& keepCentered,
                bool& includeInvisible,
                bool& createFaceSelectionGroups);

        void _SaveMetadata(
                MriGeoEntityHandle &Entity,
                const ModelData& modelData);
    
    protected:
        const char* _pluginName;
        const char* _fileName;
        MriGeoReaderHost _host;
        std::vector<std::string> _log;
        std::map<std::string, MriSelectionGroupHandle> _selectionGroups;

        bool    m_upAxisIsY;

    public:
        int _startTime;

    private:
        PXR_NS::UsdStageRefPtr _OpenUsdStage();
        FILE *_OpenLogFile();
        
};


#endif
