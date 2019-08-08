#include "ModelData.h"
#include "pxr/base/tf/stringUtils.h"
#include "pxr/usd/usd/modelAPI.h"
#include <sstream>

using namespace std;
PXR_NAMESPACE_USING_DIRECTIVE

//------------------------------------------------------------------------------
// Utilities
//------------------------------------------------------------------------------

// ...

//------------------------------------------------------------------------------
// ModelData implementation
//------------------------------------------------------------------------------

ModelData::ModelData(UsdPrim prim, string wantedUvSet)
{
    UsdModelAPI schema(prim);
    if (schema.IsModel()) 
    {
        // this might be in a shot
        fullPath = modelName = instanceName = label = modelPath =
            prim.GetPath().GetName();
        uvSet = wantedUvSet;
    }
}


ModelData& 
ModelData::operator = (const ModelData& other)
{
    fullPath = other.fullPath;
    instanceName = other.instanceName;
    modelName = other.modelName;
    prod = other.prod;
    label = other.label;
    modelPath = other.modelPath;
    uvSet = other.uvSet;

    return *this;
}

map<string, string>
ModelData::GetMetadata() const
{
    map<string, string> metadata;
    metadata["instanceName"] = instanceName;
    metadata["fullPath"] = fullPath;
    metadata["label"] = label;
    metadata["modelName"] = modelName;
    metadata["prod"] = prod;
    metadata["uvSet"] = uvSet;
    return metadata;
}
