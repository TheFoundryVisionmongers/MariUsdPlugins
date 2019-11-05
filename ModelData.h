#ifndef MODEL_DATA_H
#define MODEL_DATA_H

#include "MriGeoReaderPlugin.h"
#include "pxr/usd/usd/prim.h"

#include <string>
#include <map>

struct ModelData
{
    /* 
    This structure keeps track of valid models, 
    as defined in the pixar pipeline.
    Model Groups are not considered models for our purposes.
    One ModelData struct can have a lot of gprims.
    */
public:
    std::string fullPath;
    std::string instanceName;
    std::string modelName;
    std::string prod;
    std::string label;
    std::string modelPath;
    std::string uvSet;

    PXR_NS::UsdPrim mprim;
    std::vector<PXR_NS::UsdPrim> gprims;

    // initialize the count
    ModelData(){}
    explicit ModelData(PXR_NS::UsdPrim prim, std::string wantedUvSet = "");

    ModelData& operator = (const ModelData& other);
    std::map<std::string, std::string> GetMetadata() const;

    inline operator bool() {return fullPath != "";}
};

#endif
