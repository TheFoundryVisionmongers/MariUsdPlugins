#ifndef USD_READER_H
#define USD_READER_H

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
                const std::vector<int> &frames);
        
        static void _GetFrameList(const std::string &frameString, 
                std::vector<int> &frames);

        static void _GetVariantSelectionsList(const std::string &variantsString, 
                std::vector<PXR_NS::SdfPath> &variants);

        static FILE * _GetMetadataFile();
        static FILE * _GetLogFile();
        void _ParseUVs(MriUserItemHandle SettingsHandle, 
                GeoData::UVSet uvs, int size);
        
        void _GetMariAttributes(MriGeoEntityHandle &Entity, std::vector<int>& frames,
                std::string& frameString,
                std::vector<std::string>& requestedModelNames,
                std::vector<std::string>& requestedGprimNames,
                std::string& UVSet,
                std::vector<PXR_NS::SdfPath>& variantSelections,
                bool& keepCentered,
                bool& includeInvisible);

        void _SaveMetadata(
                MriGeoEntityHandle &Entity,
                const ModelData& modelData);
    
    protected:
        const char* _pluginName;
        const char* _fileName;
        MriGeoReaderHost _host;
        std::vector<std::string> _log;
        std::map<std::string, MriSelectionGroupHandle> _selectionGroups;


    public:
        int _startTime;

    private:
        PXR_NS::UsdStageRefPtr _OpenUsdStage();
        FILE *_OpenLogFile();
        
};


#endif
