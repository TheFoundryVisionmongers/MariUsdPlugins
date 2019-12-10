#ifndef MODEL_DATA_H
#define MODEL_DATA_H

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
