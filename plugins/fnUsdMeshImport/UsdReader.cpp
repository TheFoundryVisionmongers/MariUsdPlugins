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

#include "UsdReader.h"
#include "CameraData.h"
#include "MriGeoReaderPlugin.h"
#include "GeoData.h"
#include "ModelData.h"

#include "pxr/base/arch/systemInfo.h"
#include "pxr/base/tf/stringUtils.h"

#include "pxr/usd/usd/primRange.h"
#include "pxr/usd/usd/stageCache.h"
#include "pxr/usd/usd/stageCacheContext.h"
#include "pxr/usd/usdGeom/mesh.h"
#include "pxr/usd/usdGeom/metrics.h"
#include "pxr/usd/usdGeom/primvarsAPI.h"

#include <sstream>
#include <string>
#include <time.h>

PXR_NAMESPACE_USING_DIRECTIVE

std::string UsdReader::kNoUvSetFoundStr = "* no uv set found *";

const std::string UsdReader::kMappingSchemeOptions = "UV if available, Ptex otherwise\nForce Ptex\nUV if available, empty otherwise\nForce empty";

UsdReader::UsdReader(const char* pFileName, const PluginHosts* pluginHosts) :
    _startTime(clock()),
    _pluginName("UsdReader"),
    _fileName(pFileName),
    _pluginHosts(pluginHosts),
    _diagnosticDelegate(std::make_unique<DiagnosticDelegate>(pluginHosts))
{
    // Evaluate and store PathSubstringLists at initialization time so we don't
    // look at environment variables more than once.
    GeoData::InitializePathSubstringLists();

    TfDiagnosticMgr::GetInstance().AddDelegate(_diagnosticDelegate.get());
}

UsdReader::~UsdReader()
{
    TfDiagnosticMgr::GetInstance().RemoveDelegate(_diagnosticDelegate.get());
}

UsdStageRefPtr
UsdReader::_OpenUsdStage()
{
    _pluginHosts->geoReaderHost.trace("[%s:%d] Opening: %s", _pluginName, __LINE__, _fileName);
    
    SdfLayerRefPtr rootLayer = SdfLayer::FindOrOpen(_fileName);

    static UsdStageCache stageCache;
    UsdStageCacheContext ctx(stageCache);
    UsdStageRefPtr stage = UsdStage::Open(rootLayer);

    if (!stage)
    {
        _pluginHosts->geoReaderHost.trace("%s:%d] Cannot load usd file from %s", _pluginName, __LINE__, _fileName);
        _log.push_back("Cannot load usd file from " + std::string(_fileName) + ".");
        return NULL;
    }

    TfToken upAxis = UsdGeomGetStageUpAxis(stage);
    m_upAxisIsY = upAxis.data() == UsdGeomTokens->y;
    _pluginHosts->geoReaderHost.trace("[%s:%d] Stage up axis is : %s", _pluginName, __LINE__, m_upAxisIsY ? "y" : "z");

    return stage;
}

//------------------------------------------------------------------------------
// Pre-open a USD stage to detect the UV sets and provide parameter options

MriGeoPluginResult 
UsdReader::GetSettings(MriUserItemHandle SettingsHandle)
{
    GeoData::UVSet uvs;
    UsdStageRefPtr stage = _OpenUsdStage();

    if (!stage)
        return MRI_GPR_FAILED;
   
    UsdPrimRange range = stage->Traverse();

    if (range.empty())
    {
        _pluginHosts->geoReaderHost.trace("%s:%d] File %s is empty!", _pluginName, __LINE__, _fileName);
        _log.push_back("File "+ std::string(_fileName) + " is empty!");

        return MRI_GPR_FAILED;
    }

    int size = 0;
    for (UsdPrim prim: range)
    {
        if (GeoData::IsValidNode(prim))
        {
            GeoData::GetUvSets(prim, uvs);

        }
        size++;
    }

    _ParseUVs(SettingsHandle, uvs, size);

    return MRI_GPR_SUCCEEDED;
}

MriGeoPluginResult
UsdReader::Load(MriGeoEntityHandle &Entity)
{
    std::vector<int> frames;
    std::string loadOption, mergeOption, frameString, UVSet = "", mappingScheme;
    std::vector<std::string> requestedModelNames,requestedGprimNames;
    std::vector<SdfPath> variantSelections;
    bool conformToMariY = true;
    bool keepCentered = false;
    bool includeInvisible = false;
    bool createFaceSelectionGroups = false;

    /////// GET PARAMETERS ////////
    _GetMariAttributes(Entity,
                       loadOption, mergeOption, mappingScheme,
                       frames, frameString, requestedModelNames,
                       requestedGprimNames, UVSet, variantSelections,
                       conformToMariY, keepCentered, includeInvisible, createFaceSelectionGroups);

    bool loadFirstOnly = loadOption=="First Found";
    bool loadAll = loadOption=="All Models";
    bool keepSeparate = mergeOption=="Keep Models Separate";

    /////// READ FILE /////////
    UsdStageRefPtr stage = _OpenUsdStage();

    if (!stage)
        return MRI_GPR_FILE_OPEN_FAILED;
    
    /////// LOOP THROUGH ALL PATHS ////////
    UsdPrimRange range = stage->Traverse();

    if (range.empty())
    {
        _pluginHosts->geoReaderHost.trace("%s:%d] File %s is empty!", _pluginName, __LINE__, _fileName);
        _log.push_back("File "+ std::string(_fileName) + " is empty!");
        return MRI_GPR_FAILED;
    }

    // Get the stage prim path to set the root name for USD export
    UsdPrim stagePrim = stage->GetDefaultPrim();
    SdfPath stagePrimPath = stagePrim.GetPath();
    std::string stagePrimPathString = stagePrimPath.GetString();

    MriAttributeValue stagePrimValue;
    stagePrimValue.m_Type = MRI_ATTR_STRING;
    stagePrimValue.m_pString = stagePrimPathString.c_str();
    _pluginHosts->geoReaderHost.setAttribute(Entity, "StagePrimPath", &stagePrimValue);

    MriAttributeValue uvSetValue;
    uvSetValue.m_Type = MRI_ATTR_STRING;
    uvSetValue.m_pString = UVSet.c_str();
    _pluginHosts->geoReaderHost.setAttribute(Entity, "UvSetName", &uvSetValue);
    
    // variables used to coordinate which model should be loaded
    bool loadThisModel = false;
    bool oneModelLoaded = false;
    ModelData* currentModelData = nullptr;
    std::vector<ModelData*> modelDataList;
    std::vector<CameraData> cameraDataList;
    
    for (auto primIt = range.begin(); primIt != range.end(); ++primIt)
    {
        // Check to see if this path matches a variant
        SdfPath path = primIt->GetPath();
        for(auto it = variantSelections.begin(); it != variantSelections.end(); ++it) 
        {
            // The user has requested a variant selection for this prim through the variants parameter.
            // If it exists, let's set it.
            if (it->GetAbsoluteRootOrPrimPath() == path) {
                std::pair<std::string, std::string> variantSelection = it->GetVariantSelection();
                UsdVariantSet  vs = primIt->GetVariantSet(variantSelection.first);
                if (vs && vs.IsValid() && vs.HasAuthoredVariant(variantSelection.second)) 
                {
                    vs.SetVariantSelection(variantSelection.second);
                    _pluginHosts->geoReaderHost.trace("set variant set %s  =  %s on prim %s",
                                                      variantSelection.first.c_str(),
                                                      variantSelection.second.c_str(),
                                                      path.GetString().c_str());
                }
            }
        }

        // get this model Data
        ModelData thisModelData (*primIt, UVSet);
        if (thisModelData)
        {
            if(oneModelLoaded && loadFirstOnly)
            {
                // loaded one model already, so this is the second model. break now
                break;
            }

            if(loadAll || loadFirstOnly)
            {
                // load this model because "All" or "First Found" is requested
                loadThisModel = true;
            }
            else
            {
                // otherwise, load this model only if it's specified in "Model Names"
                std::vector<std::string>::iterator it = std::find(requestedModelNames.begin(), requestedModelNames.end(), primIt->GetPath().GetText());
                loadThisModel = it!=requestedModelNames.end();
            }

            // Keep metadata for this model
            if (loadThisModel) 
            {
                currentModelData = new ModelData(thisModelData);
                modelDataList.push_back(currentModelData);
            }
            else
            {
                // Reset currentModelData to null so that the gprims belonging to this model will not get loaded
                currentModelData = nullptr;
            }
        }

        if (!loadThisModel) 
        {
            // this is not a model the user opted in.
            continue;
        }
        UsdGeomImageable imageable = UsdGeomImageable(*primIt);
        if (!includeInvisible && imageable)
        {
            TfToken visibility = imageable.ComputeVisibility();
            if(visibility == UsdGeomTokens->invisible) 
            {
                primIt.PruneChildren();
                continue;
            }
        }

        if (CameraData::IsValidNode(*primIt))
        {
            cameraDataList.emplace_back(CameraData(*primIt));
            continue;
        }

        if (!GeoData::IsValidNode(*primIt)) 
        {
            // not even a gprim.
            continue;
        }

        // If we've requested specific gprims and 
        // this gprim isnt' in that list, continue.
        // We need to search using the full path of the current
        // gprim as well as the simple name, since either one
        // may have been passed in.
        // XXX This might start to get costly with very large lists of
        // gprims. 2(O^2). 

        if (
            requestedGprimNames.size() > 0 &&
            (std::find(requestedGprimNames.begin(),
                       requestedGprimNames.end(),
                       path.GetName()) == requestedGprimNames.end()) &&
            (std::find(requestedGprimNames.begin(),
                       requestedGprimNames.end(),
                       path.GetText()) == requestedGprimNames.end()) 
            ) 
        {
            continue;
        }

        if (currentModelData)
        {
            currentModelData->gprims.push_back(*primIt);
            oneModelLoaded = true;
        }

        else {
            _pluginHosts->geoReaderHost.trace("[%s] Could not make mari geo entity with uv set %s for prim %s", _pluginName, UVSet.c_str(), path.GetString().c_str());
            _log.push_back("Could not make mari geo entity with uv set " + UVSet + " for prim " + path.GetString() + ".");
        }
    }

    int modelCount = 0;
    for (ModelData* modelData: modelDataList)
    {
        if (modelData->gprims.size()>0)
        {
            ++modelCount;
        }
    }

    if (modelCount == 0)
    {
        // No UsdGeomMesh found to load -> error out now!

        _pluginHosts->geoReaderHost.trace("[%s:%d] No model of type UsdGeomMesh found to load in %s", _pluginName, __LINE__, _fileName);
        _log.push_back("> No model of type UsdGeomMesh found to load in " + std::string(_fileName));

        return MRI_GPR_FAILED;
    }

    bool createChildren = modelCount>1 && keepSeparate;

    if (createChildren)
    {
        _pluginHosts->geoReaderHost.setEntityType(Entity, MRI_SET_ENTITY);
    }

    for (const auto& cameraData : cameraDataList)
    {
        cameraData.MakeEntity(_pluginHosts, Entity);
    }

    for (ModelData* modelData: modelDataList)
    {
        if (modelData->gprims.size()==0)
        {
            // No gprim i.e. no geometry data
            continue;
        }

        MriGeoEntityHandle entityToPopulate = Entity;
        if (createChildren)
        {
            MriGeoEntityHandle childEntity;
            _pluginHosts->geoReaderHost.createChildGeoEntity(Entity, _fileName, &childEntity);
            _pluginHosts->geoReaderHost.setEntityName(childEntity, modelData->instanceName.c_str());

            entityToPopulate = childEntity; 
        }

        bool ValidEntity = false;
        for (auto prim: modelData->gprims)
        {
            // Create a mari-compatible geometry
            GeoData Geom(prim, UVSet, mappingScheme, frames, conformToMariY, m_upAxisIsY, keepCentered, modelData->mprim, _pluginHosts, _log);
            if (Geom)
            {
                _pluginHosts->geoReaderHost.trace("[%s:%d] * Found importable mesh %s", _pluginName, __LINE__, prim.GetPath().GetName().c_str());

                // detect handle id
                std::string handle = "";
                TfToken orientation;
                UsdGeomGprim gprim(prim);
                if (gprim) {
                    TfToken gprimHandleIdToken ("__gprimHandleid");
                    UsdGeomPrimvarsAPI gprimApi(gprim);
                    UsdGeomPrimvar primvar = gprimApi.GetPrimvar(gprimHandleIdToken);
                    if (!primvar)
                    {
                        TfToken handleIdToken("__handleId");
                        primvar = gprimApi.GetPrimvar(handleIdToken);
                    }
                    VtValue value;
                    primvar.ComputeFlattened(&value);
                    handle = TfStringify(value);

                    UsdAttribute orientationAttr = gprim.GetOrientationAttr();
                    orientationAttr.Get(&orientation);
                }
                if (handle.empty()) {
                    handle = prim.GetPath().GetText();
                }

                Geom.SetRightHandedWindingOrder(orientation != TfToken("leftHanded"));

                _MakeGeoEntity(Geom, entityToPopulate, handle, frames, createFaceSelectionGroups);

                ValidEntity = true;
            }
            else
            {
                _pluginHosts->geoReaderHost.trace("[%s:%d] X Could not load mesh %s", _pluginName, __LINE__, prim.GetPath().GetName().c_str());
                --modelCount;
            }
        }

        // Save on metadata file
        if (ValidEntity)
        {
            _SaveMetadata( Entity, *modelData);
        }
    }

    MriGeoPluginResult result = MRI_GPR_SUCCEEDED;

    if (modelDataList.size()==0 || modelCount == 0)
    {
        _pluginHosts->geoReaderHost.trace("[%s:%d] No valid geometry found in %s", _pluginName, __LINE__, _fileName);
        _log.push_back("> No valid geometry found in " + std::string(_fileName));

        result = MRI_GPR_FAILED;
    }

    // clean up
    for(ModelData* modelData: modelDataList)
    {
        delete modelData;
    }

    return result;
}



void 
UsdReader::_GetFrameList(const std::string &frameString, std::vector<int> &frames)
{
    std::vector<std::string> framesStringTokens;
    framesStringTokens = TfStringTokenize(frameString, ",");
    
    for (auto it = framesStringTokens.begin(); it != framesStringTokens.end(); ++it)
    {
        // Process range values
        std::vector<std::string> rangeStringTokens = TfStringTokenize(*it, "-");
        if (!rangeStringTokens.empty() && rangeStringTokens.size() == 2)
        {
            int startFrame = int(TfStringToDouble(rangeStringTokens[0]));
            int endFrame = int(TfStringToDouble(rangeStringTokens[1]));
            for (int frame = startFrame; frame <= endFrame; ++frame)
            {
                frames.push_back(frame);
            }

        }
        else
        {
            // Single frame
            frames.push_back(int(TfStringToDouble(*it)));
        }
    }

    // Reorder our frames
    std::sort(frames.begin(), frames.begin());
}

void 
UsdReader::_GetVariantSelectionsList(const std::string &variantsString, std::vector<SdfPath> &variants)
{
    std::vector<std::string> variantsStringTokens;
    variantsStringTokens = TfStringTokenize(variantsString, " ");
    
    for (auto it = variantsStringTokens.begin(); it != variantsStringTokens.end(); ++it)
    {
        SdfPath path = SdfPath(*it);
        if (path.IsPrimVariantSelectionPath() )
        {
            variants.push_back(path);
        }
    }
}

MriGeoPluginResult UsdReader::_MakeGeoEntity(GeoData &Geom, MriGeoEntityHandle &Entity, std::string label, const std::vector<int> &frames, bool createFaceSelectionGroups)
{
    MriGeoDataHandle FaceVertexCounts{}, Vertices{}, Normals{}, VertexIndices{}, NormalIndices{};
    MriGeoDataHandle UVs{}, UVIndices{};
    MriGeoDataHandle CreaseIndices{}, CreaseLengths{}, CreaseSharpness{}, CornerIndices{}, CornerSharpness{}, Holes{};
    MriGeoObjectHandle MeshObject{};
    MriGeoPluginResult Result{};

    // 1 Create a version - not needed, as Mari creates a default one for us

    // 2. Create our geometry data channels
    CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                           Geom.GetVertices(0),
                                                           Geom.GetNumPoints() * sizeof(float),
                                                           MRI_GDT_FLOAT_BUFFER,
                                                           MRI_GDR_MESH_VERTICES,
                                                           &Vertices));
    CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                           Geom.GetVertexIndices(),
                                                           Geom.GetNumVertexIndices() * sizeof(unsigned int),
                                                           MRI_GDT_U32_BUFFER,
                                                           MRI_GDR_MESH_VERTEX_INDICES,
                                                           &VertexIndices));
    CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                           Geom.GetFaceVertexCounts(),
                                                           Geom.GetNumFaceVertexCounts() * sizeof(unsigned int),
                                                           MRI_GDT_U32_BUFFER,
                                                           MRI_GDR_MESH_FACE_VERTEX_COUNTS,
                                                           &FaceVertexCounts));

    if (Geom.HasNormals())
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                               Geom.GetNormals(),
                                                               Geom.GetNumNormals() * sizeof(float),
                                                               MRI_GDT_FLOAT_BUFFER,
                                                               MRI_GDR_MESH_NORMALS,
                                                               &Normals));
        CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                               Geom.GetNormalIndices(),
                                                               Geom.GetNumVertexIndices() * sizeof(unsigned int),
                                                               MRI_GDT_U32_BUFFER,
                                                               MRI_GDR_MESH_NORMAL_INDICES,
                                                               &NormalIndices));
    }
    if (Geom.HasUVs())
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                               Geom.GetUVs(),
                                                               Geom.GetNumUvs() * sizeof(float),
                                                               MRI_GDT_FLOAT_BUFFER,
                                                               MRI_GDR_MESH_UV0,
                                                               &UVs));
        CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                               Geom.GetUVIndices(),
                                                               Geom.GetNumVertexIndices() * sizeof(unsigned int),
                                                               MRI_GDT_U32_BUFFER,
                                                               MRI_GDR_MESH_UV0_INDICES,
                                                               &UVIndices));
    }

    if (Geom.GetNumCreaseIndices() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                               Geom.GetCreaseLengths(),
                                                               Geom.GetNumCreaseLengths() * sizeof(unsigned int),
                                                               MRI_GDT_U32_BUFFER,
                                                               MRI_GDR_MESH_SUBD_CREASE_LENGTHS,
                                                               &CreaseLengths));
    }
    if (Geom.GetNumCreaseLengths() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                               Geom.GetCreaseIndices(),
                                                               Geom.GetNumCreaseIndices() * sizeof(unsigned int),
                                                               MRI_GDT_U32_BUFFER,
                                                               MRI_GDR_MESH_SUBD_CREASE_INDICES,
                                                               &CreaseIndices));
    }
    if (Geom.GetNumCreaseSharpness() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                               Geom.GetCreaseSharpness(),
                                                               Geom.GetNumCreaseSharpness() * sizeof(float),
                                                               MRI_GDT_FLOAT_BUFFER,
                                                               MRI_GDR_MESH_SUBD_CREASE_SHARPNESS,
                                                               &CreaseSharpness));
    }
    if (Geom.GetNumCornerIndices() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                               Geom.GetCornerIndices(),
                                                               Geom.GetNumCornerIndices() * sizeof(unsigned int),
                                                               MRI_GDT_U32_BUFFER,
                                                               MRI_GDR_MESH_SUBD_CORNER_INDICES,
                                                               &CornerIndices));
    }
    if (Geom.GetNumCornerSharpness() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                               Geom.GetCornerSharpness(),
                                                               Geom.GetNumCornerSharpness() * sizeof(float),
                                                               MRI_GDT_FLOAT_BUFFER,
                                                               MRI_GDR_MESH_SUBD_CORNER_SHARPNESS,
                                                               &CornerSharpness));
    }
    if (Geom.GetNumHoleIndices() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.createGeoData(Entity,
                                                               Geom.GetHoleIndicess(),
                                                               Geom.GetNumHoleIndices() * sizeof(unsigned int),
                                                               MRI_GDT_U32_BUFFER,
                                                               MRI_GDR_MESH_SUBD_HOLES,
                                                               &Holes));
    }

    // 3. Create Mesh and add data channels to it
    CHECK_RESULT(_pluginHosts->geoReaderHost.createMeshObject(Entity, label.c_str(), Geom.GetNumFaceVertexCounts(), &MeshObject));
    MriAttributeValue RightHandedWindingOrder;
    RightHandedWindingOrder.m_Type = MRI_ATTR_BOOL;
    RightHandedWindingOrder.m_Int = Geom.IsRightHandWindingOrder();
    _pluginHosts->geoReaderHost.setAttribute(MeshObject, "RightHandedWindingOrder", &RightHandedWindingOrder);

    CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, Vertices));
    CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, VertexIndices));
    if (Geom.HasNormals())
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, Normals));
        CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, NormalIndices));
    }
    CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, FaceVertexCounts));
    if (Geom.HasUVs())
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, UVs));
        CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, UVIndices));
    }

    if (Geom.GetNumCreaseIndices() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, CreaseIndices));
    }
    if (Geom.GetNumCreaseLengths() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, CreaseLengths));
    }
    if (Geom.GetNumCreaseSharpness() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, CreaseSharpness));
    }
    if (Geom.GetNumCornerIndices() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, CornerIndices));
    }
    if (Geom.GetNumCornerSharpness() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, CornerSharpness));
    }
    if (Geom.GetNumHoleIndices() > 0)
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.addGeoDataToObject(Entity, MeshObject, Holes));
    }
    if (Geom.IsSubdivMesh())
    {
        CHECK_RESULT(_pluginHosts->geoReaderHost.setSubdivisionOnMeshObject(Entity,
                                                                            MeshObject,
                                                                            Geom.SubdivisionScheme().c_str(),
                                                                            Geom.InterpolateBoundary(),
                                                                            Geom.FaceVaryingLinearInterpolation(),
                                                                            Geom.PropagateCorner(),
                                                                            Geom.TriangleSubdivision()));
    }

    // Load animated frames
    // The structures before have added a default entry in the channels' data refererences with frame=0
    for (unsigned int frameIndex = 0; frameIndex<frames.size(); ++frameIndex)
    {
        int frame = frames[frameIndex];
        if (frame == 0)
        {
            // We've already added ddi references for frame = 0, no need to do that again - Skip
            continue;
        }

        CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                    Vertices,
                                                                    frame,
                                                                    Geom.GetVertices(frame),
                                                                    Geom.GetNumPoints() * sizeof(float)));

        CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                    VertexIndices,
                                                                    frame,
                                                                    Geom.GetVertexIndices(),
                                                                    Geom.GetNumVertexIndices() * sizeof(unsigned int)));

        CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                    FaceVertexCounts,
                                                                    frame,
                                                                    Geom.GetFaceVertexCounts(),
                                                                    Geom.GetNumFaceVertexCounts() * sizeof(unsigned)))
        if (Geom.HasNormals())
        {
            CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                        Normals,
                                                                        frame,
                                                                        Geom.GetNormals(),
                                                                        Geom.GetNumNormals() * sizeof(float)));

            // REQUIRED To prevent Mari from automatically reindexing for latter frames and creating mangled rendereing
            CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                        NormalIndices,
                                                                        frame,
                                                                        Geom.GetNormalIndices(),
                                                                        Geom.GetNumVertexIndices() * sizeof(unsigned int)));
        }
        if (Geom.HasUVs())
        {
            CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                        UVs,
                                                                        frame,
                                                                        Geom.GetUVs(),
                                                                        Geom.GetNumUvs() * sizeof(float)));
            // REQUIRED To prevent Mari from automatically reindexing for latter frames and creating mangled rendereing
            CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                        UVIndices,
                                                                        frame,
                                                                        Geom.GetUVIndices(),
                                                                        Geom.GetNumVertexIndices() * sizeof(unsigned int)));
        }

        if (Geom.GetNumCreaseIndices() > 0)
        {
            CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                        CreaseLengths,
                                                                        frame,
                                                                        Geom.GetCreaseLengths(),
                                                                        Geom.GetNumCreaseLengths() * sizeof(unsigned int)));
        }
        if (Geom.GetNumCreaseLengths() > 0)
        {
            CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                        CreaseIndices,
                                                                        frame,
                                                                        Geom.GetCreaseIndices(),
                                                                        Geom.GetNumCreaseIndices() * sizeof(unsigned int)));
        }
        if (Geom.GetNumCreaseSharpness() > 0)
        {
            CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                        CreaseSharpness,
                                                                        frame,
                                                                        Geom.GetCreaseSharpness(),
                                                                        Geom.GetNumCreaseSharpness() * sizeof(float)));
        }
        if (Geom.GetNumCornerIndices() > 0)
        {
            CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                        CornerIndices,
                                                                        frame,
                                                                        Geom.GetCornerIndices(),
                                                                        Geom.GetNumCornerIndices() * sizeof(unsigned int)));
        }
        if (Geom.GetNumCornerSharpness() > 0)
        {
            CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                        CornerSharpness,
                                                                        frame,
                                                                        Geom.GetCornerSharpness(),
                                                                        Geom.GetNumCornerSharpness() * sizeof(float)));
        }
        if (Geom.GetNumHoleIndices() > 0)
        {
            CHECK_RESULT(_pluginHosts->geoReaderHost.setGeoDataForFrame(Entity,
                                                                        Holes,
                                                                        frame,
                                                                        Geom.GetHoleIndicess(),
                                                                        Geom.GetNumHoleIndices() * sizeof(unsigned int)));
        }
    }

    // 4. Add Mesh object to version - unneeded since we did not create a default version

    // 5. Add face selection groups
    if (createFaceSelectionGroups)
    {
        char pszBuffer[256];

        MriSelectionGroupHandle FaceSelection;

        snprintf(pszBuffer, sizeof(pszBuffer), "Faces_%s", label.c_str());
        CHECK_RESULT(_pluginHosts->geoReaderHost.createSelectionGroup(Entity, pszBuffer, &FaceSelection));
        CHECK_RESULT(_pluginHosts->geoReaderHost.addFacesToSelectionGroup(Entity, FaceSelection, MeshObject, Geom.GetFaceSelectionIndices(), Geom.GetNumFaceVertexCounts()));
    }

    return MRI_GPR_SUCCEEDED;
}

void
UsdReader::_ParseUVs(MriUserItemHandle SettingsHandle,
                           GeoData::UVSet uvs, 
                           int size)
{
    std::string choices = "";
    for (GeoData::UVSet::iterator it = uvs.begin(); it != uvs.end(); ++it)
    {
        if (choices.length() > 0)
        {
            // Already have a previous option, append new line
            choices += "\n";
        }

        std::stringstream oss;
        oss << it->first << " (" << it->second << "/" << size <<  ")";
        choices += oss.str();
    }

    if (uvs.empty())
    {
        choices = kNoUvSetFoundStr;
    }
   
    MriAttributeValue UVValue;
    UVValue.m_Type = MRI_ATTR_STRING_LIST;
    UVValue.m_pString = choices.c_str();
    _pluginHosts->geoReaderHost.setAttribute(SettingsHandle, "UV Set", &UVValue);
}

void
UsdReader::_GetMariAttributes(MriGeoEntityHandle &Entity,
                                    std::string& loadOption,
                                    std::string& mergeOption,
                                    std::string& mappingScheme,
                                    std::vector<int>& frames,
                                    std::string& frameString,
                                    std::vector<std::string>& requestedModelNames,
                                    std::vector<std::string>& requestedGprimNames,
                                    std::string& UVSet,
                                    std::vector<SdfPath>& variantSelections,
                                    bool& conformToMariY,
                                    bool& keepCentered,
                                    bool& includeInvisible,
                                    bool& createFaceSelectionGroups)
{
    MriAttributeValue Value;

    // detect requested load option
    if (_pluginHosts->geoReaderHost.getAttribute(Entity, "Load", &Value) == MRI_UPR_SUCCEEDED)
        loadOption = Value.m_pString;

    _pluginHosts->geoReaderHost.trace("%s:%d] requested Load Option %s", _pluginName, __LINE__, loadOption.c_str());

    if (loadOption == "First Found\nAll Models\nSpecified Models in Model Names")
    {
        // Default when unset
        loadOption = "All Models";
    }

    // detect requested merge option
    if (_pluginHosts->geoReaderHost.getAttribute(Entity, "Merge Type", &Value) == MRI_UPR_SUCCEEDED)
        mergeOption = Value.m_pString;
    _pluginHosts->geoReaderHost.trace("%s:%d] requested Merge Option %s", _pluginName, __LINE__, mergeOption.c_str());

    if (mergeOption == "Merge Models\nKeep Models Separate")
    {
        // Default when unset
        mergeOption = "Merge Models";
    }

    // detect requested model name
    std::string modelNamesString;
    if (_pluginHosts->geoReaderHost.getAttribute(Entity, "Model Names", &Value) == MRI_UPR_SUCCEEDED)
        modelNamesString = Value.m_pString;

    requestedModelNames = TfStringTokenize(modelNamesString, ",");

    _pluginHosts->geoReaderHost.trace("%s:%d] requested modelNames %s", _pluginName, __LINE__, modelNamesString.c_str());

    // detect requested UV set
    if (_pluginHosts->geoReaderHost.getAttribute(Entity, "UV Set", &Value) == MRI_UPR_SUCCEEDED)
    {
        if (Value.m_pString == kNoUvSetFoundStr)
        {
            UVSet = "";
            _pluginHosts->geoReaderHost.trace("%s:%d] No uv set found", _pluginName, __LINE__);
        }
        else
        {
            UVSet = Value.m_pString;
            UVSet = UVSet.substr(0, UVSet.find(" "));

            _pluginHosts->geoReaderHost.trace("%s:%d] Using uv set %s", _pluginName, __LINE__, UVSet.c_str());
        }
    }

    // Mapping scheme option
    if (_pluginHosts->geoReaderHost.getAttribute(Entity, "Mapping Scheme", &Value) == MRI_UPR_SUCCEEDED)
        mappingScheme = Value.m_pString;

    _pluginHosts->geoReaderHost.trace("%s:%d] Mappping scheme Option %s", _pluginName, __LINE__, mappingScheme.c_str());

    if (mappingScheme == kMappingSchemeOptions)
    {
        // Default when unset
        mappingScheme = "UV if available, Ptex otherwise";
    }

    // detect requested frames
    if (_pluginHosts->geoReaderHost.getAttribute(Entity, "Frame Numbers", &Value) == MRI_UPR_SUCCEEDED)
        frameString = Value.m_pString;

    _GetFrameList(frameString, frames);
    _pluginHosts->geoReaderHost.trace("%s:%d] requested %lu frames", _pluginName, __LINE__, frames.size());

    // detect requested gprim names
    std::string gprimNamesString;
    if (_pluginHosts->geoReaderHost.getAttribute(Entity, "Gprim Names", &Value) == MRI_UPR_SUCCEEDED)
        gprimNamesString = Value.m_pString;
    requestedGprimNames = TfStringTokenize(gprimNamesString, ",");

    _pluginHosts->geoReaderHost.trace("%s:%d] requested gprimString %s", _pluginName, __LINE__, gprimNamesString.c_str());

    std::string variantsString;
    if (_pluginHosts->geoReaderHost.getAttribute(Entity, "Variants", &Value) == MRI_UPR_SUCCEEDED)
    {
        variantsString = Value.m_pString;
        _GetVariantSelectionsList(variantsString, variantSelections);
        _pluginHosts->geoReaderHost.trace("%s:%d] Using variants %s", _pluginName, __LINE__, variantsString.c_str());
    }

    // conform to Mari Y is up
    if(_pluginHosts->geoReaderHost.getAttribute(Entity, "Conform to Mari Y as up", &Value) == MRI_UPR_SUCCEEDED )
        conformToMariY = (Value.m_Int !=0);
    _pluginHosts->geoReaderHost.trace("%s:%d] Conform to Mari Y is up : %d", _pluginName, __LINE__, conformToMariY);

    // detect if we want to ignore model transforms
    if(_pluginHosts->geoReaderHost.getAttribute(Entity, "Keep Centered", &Value) == MRI_UPR_SUCCEEDED )
        keepCentered = (Value.m_Int !=0);
    if( keepCentered )
        _pluginHosts->geoReaderHost.trace("%s:%d] Discarding model transforms.", _pluginName, __LINE__);

    // detect if we want to include invisible gprims
    if(_pluginHosts->geoReaderHost.getAttribute(Entity, "Include Invisible", &Value) == MRI_UPR_SUCCEEDED )
        includeInvisible = (Value.m_Int !=0);
    if( !includeInvisible )
        _pluginHosts->geoReaderHost.trace("%s:%d] Discarding invisible gprims.", _pluginName, __LINE__);

    // detect if we want to create face selection groups
    if(_pluginHosts->geoReaderHost.getAttribute(Entity, "Create Face Selection Group per mesh", &Value) == MRI_UPR_SUCCEEDED )
        createFaceSelectionGroups = (Value.m_Int !=0);

    if( createFaceSelectionGroups )
        _pluginHosts->geoReaderHost.trace("%s:%d] Will create face selection groups.", _pluginName, __LINE__);
}

void
UsdReader::_SaveMetadata(
        MriGeoEntityHandle &Entity,
        const ModelData& modelData)
{
    MriAttributeValue Value;
    Value.m_Type = MRI_ATTR_STRING;
    std::map<std::string, std::string> metadata = modelData.GetMetadata();
    _pluginHosts->geoReaderHost.trace("%s:%d] Using metadata setAttribute (>2.0)", _pluginName, __LINE__);
    for (auto it = metadata.begin(); it!=metadata.end();++it)
    {
        Value.m_pString = it->second.c_str();
        _pluginHosts->geoReaderHost.trace("%s:%d] setting metadata %s to %s", _pluginName, __LINE__, it->first.c_str(), it->second.c_str());
        _pluginHosts->geoReaderHost.setAttribute(Entity, it->first.c_str(), &Value);
    }
}

std::string UsdReader::GetLog()
{
    // This code block performs typical join() operation
    std::ostringstream os;
    std::copy(_log.begin(), _log.end(), std::ostream_iterator<std::string>(os,"\n"));
    std::string result = os.str();
    if(result.size()>0)
    {
        result.erase(result.size()-1);
    }

    return result;
}

