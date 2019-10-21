#include "UsdReader.h"
#include "MriGeoReaderPlugin.h"
#include "GeoData.h"
#include "ModelData.h"

#include "pxr/base/arch/systemInfo.h"
#include "pxr/base/tf/stringUtils.h"

#include "pxr/usd/usd/primRange.h"
#include "pxr/usd/usd/stageCache.h"
#include "pxr/usd/usd/stageCacheContext.h"
#include "pxr/usd/usdGeom/mesh.h"
#include "pxr/usd/ar/resolver.h"
#include "pxr/usd/ar/resolverContext.h"
#include <sstream>
#include <string>
#include <time.h>

using namespace std;
PXR_NAMESPACE_USING_DIRECTIVE

UsdReader::UsdReader(const char* pFileName, 
                                 MriGeoReaderHost &pHost) :
    _pluginName("UsdReader"),
    _fileName(pFileName),
    _host(pHost),
    _startTime(clock())
{
    // Evaluate and store PathSubstringLists at initialization time so we don't
    // look at environment variables more than once.
    GeoData::InitializePathSubstringLists();
}
UsdStageRefPtr
UsdReader::_OpenUsdStage()
{
    _host.trace("[%s] Opening: %s", _pluginName, _fileName);
    
    SdfLayerRefPtr rootLayer = SdfLayer::FindOrOpen(_fileName);

    bool isAbsPath = strlen(_fileName) > 0 and _fileName[0] == '/';
    std::string contextPath = 
        isAbsPath ? TfGetPathName(_fileName) : ArchGetCwd(); 
    ArResolver& resolver = ArGetResolver();
    ArResolverContext pathResolverContext = 
        resolver.CreateDefaultContextForAsset(contextPath);
    
    static UsdStageCache stageCache;
    UsdStageCacheContext ctx(stageCache);
    UsdStageRefPtr stage = UsdStage::Open(rootLayer, pathResolverContext);

    if (!stage)
    {
        _host.trace("[%s] Cannot load usd file from %s", _pluginName, _fileName);
        _log.push_back("Cannot load usd file from " + std::string(_fileName) + ".");
        return NULL;
    }

    // reload the stage to flush any USD level cache
    stage->Reload();

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
   
    UsdPrimRange primRange = stage->Traverse();

    if (!primRange)
    {
        _host.trace("[%s] File %s is empty!", _pluginName, _fileName);
        _log.push_back("File "+ std::string(_fileName) + " is empty!");

        return MRI_GPR_FAILED;
    }

    int size = 0;
    for (auto primIt = primRange.cbegin(); primIt != primRange.cend(); )
    {
        if (GeoData::IsValidNode((*primIt))) 
        {
            GeoData::GetUvSets(*primIt, uvs);
        }
        ++primIt;
        size++;
    }
        
    if (uvs.size() > 0)
    {
        _ParseUVs(SettingsHandle, uvs, size);
    }

    return MRI_GPR_SUCCEEDED;
}

MriGeoPluginResult
UsdReader::Load(MriGeoEntityHandle &Entity)
{
    vector<int> frames;
    std::string frameString, UVSet = "map1";
    vector<std::string> requestedModelNames,requestedGprimNames;
    vector<SdfPath> variantSelections;
    bool keepCentered = false;
    bool includeInvisible = false;

    /////// GET PARAMETERS ////////
    _GetMariAttributes(Entity, frames, frameString, requestedModelNames,
                       requestedGprimNames, UVSet, variantSelections, 
                       keepCentered, includeInvisible);
    
    /////// READ FILE /////////
    UsdStageRefPtr stage = _OpenUsdStage();

    if (!stage)
        return MRI_GPR_FILE_OPEN_FAILED;
    
    /////// LOOP THROUGH ALL PATHS ////////
    UsdPrimRange primRange = stage->Traverse();

    if (!primRange)
    {
        _host.trace("[%s] File %s is empty!", _pluginName, _fileName);
        _log.push_back("File "+ std::string(_fileName) + " is empty!");
        return MRI_GPR_FAILED;
    }
    
    // variables used to coordinate which model should be loaded
    UsdPrim currentModel;
    bool loadThisModel = false, someModelLoaded = false;
    ModelData currentModelData;
    
    for (auto primIt = primRange.cbegin(); primIt != primRange.cend(); )
    {


        // Check to see if this path matches a variant
        SdfPath path = primIt->GetPath();
        for(vector<SdfPath>::iterator it = variantSelections.begin();
            it != variantSelections.end();
            ++it) 
        {
            // The user has requested a variant selection for this prim through the variants parameter.
            // If it exists, let's set it.
            if (it->GetAbsoluteRootOrPrimPath() == path) {
                pair<string,string> variantSelection = it->GetVariantSelection();
                UsdVariantSet  vs = primIt->GetVariantSet(variantSelection.first);
                if (vs && vs.IsValid() && vs.HasAuthoredVariant(variantSelection.second)) 
                {
                    vs.SetVariantSelection(variantSelection.second);
                    _host.trace("set variant set %s  =  %s on prim %s", 
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
            // do we want to load any good model, 
            // or this is the one we requested?
            std::vector<std::string>::iterator it = std::find(requestedModelNames.begin(), requestedModelNames.end(), thisModelData.instanceName);
            loadThisModel = it!=requestedModelNames.end();

            // Keep metadata for this model
            if (loadThisModel) 
            {
                currentModel = *primIt;
                currentModelData = thisModelData;
            }

            // if this node is a model, it is not a gprim: continue to next.
            ++primIt;
            continue;
        }

        if (not loadThisModel) 
        {
            // this is not a model the user opted in.
            ++primIt;
            continue;
        }
        UsdGeomImageable imageable = UsdGeomImageable(*primIt);
        TfToken visibility; 
        if (!includeInvisible && imageable && imageable.GetVisibilityAttr().Get(&visibility))
        {
            if(visibility == UsdGeomTokens->invisible) 
            {
                _host.trace("[%s] %s Is invisible", 
                    _pluginName, primIt->GetPath().GetText());
                primIt.PruneChildren();
                ++primIt;
                continue;
            } else {
                _host.trace("[%s] %s Is visible", 
                    _pluginName, primIt->GetPath().GetText());
            }
                
        }

        if (not GeoData::IsValidNode(*primIt)) 
        {
            _host.trace("[%s] %s Not a valid node", 
                    _pluginName, primIt->GetPath().GetText());
            // not even a gprim.
            ++primIt;
            continue;
        }


        // If we've requested specific gprims and 
        // this gprim isnt' in that list, continue.
        // We need to search using the full path of the current
        // gprim as well as the simple name, since either one
        // may have been passed in.
        // XXX This might start to get costly with very large lists of
        // gprims. 2(O^2). 


        _host.trace("[%s] looking for %s and %s in requested names %d.", 
                    _pluginName, path.GetName().c_str(), path.GetText(), requestedGprimNames.size());
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
            ++primIt;
            continue;
        }

        // Create a mari-compatible geometry
        GeoData Geom(*primIt, UVSet, 
                     frames, keepCentered, currentModel, _host, _log);
        if (Geom) 
        {

            _host.trace("[%s] %s, found importable mesh", 
                        _pluginName, path.GetName().c_str());

            // detect handle id
            std::string handle = "";
            UsdGeomGprim gprim(*primIt);
            if (gprim) {
                TfToken gprimHandleIdToken ("__gprimHandleid"); 
                UsdGeomPrimvar primvar = gprim.GetPrimvar(gprimHandleIdToken); 
                if (not primvar) {
                    TfToken handleIdToken("__handleId"); 
                    primvar = gprim.GetPrimvar(handleIdToken); 
                }
                VtValue value;
                primvar.ComputeFlattened(&value);
                handle = TfStringify(value); 
            }
            if (handle.empty()) {
                handle = primIt->GetPath().GetText();
            }

            //TODO This should go somewhere else
            _host.setEntityType(Entity, MRI_SET_ENTITY);

            MriGeoEntityHandle ChildEntity;
            _host.createChildGeoEntity(Entity, _fileName, &ChildEntity);
            _host.setEntityName(ChildEntity, currentModelData.instanceName.c_str());

            _MakeGeoEntity(Geom, ChildEntity,
                handle, frames);

            // found some acceptable geometry
            someModelLoaded = true;
        }

        ++primIt;
    }

    // Save on metadata file
    if (someModelLoaded)
    {
        _SaveMetadata( Entity, currentModelData);
        return MRI_GPR_SUCCEEDED;
    }
    else
    {
        std::string requestedModelName;
        for(const std::string& name: requestedModelNames)
        {
            if(requestedModelNames.size()>0)
            {
                requestedModelName.append(",");
            }
            requestedModelName.append(name);
        }

        _host.trace("[%s] No valid geometry with uv set %s found in %s",
            _pluginName, UVSet.c_str(), _fileName);
        _host.trace("[%s] Was looking for %s", 
            _pluginName, requestedModelName.c_str());
        _log.push_back("No valid geometry with uv set " + UVSet +
                       " found in " + std::string(_fileName) + ".");
        _log.push_back("Was looking for " + requestedModelName);


        return MRI_GPR_FAILED;
    }
}



void 
UsdReader::_GetFrameList(const string &frameString, vector<int> &frames)
{
    std::vector<std::string> framesStringTokens;
    framesStringTokens = TfStringTokenize(frameString, ",");
    
    for (vector<string>::iterator it = framesStringTokens.begin();
            it != framesStringTokens.end();
            ++it)
        frames.push_back(int(TfStringToDouble(*it)));
}

void 
UsdReader::_GetVariantSelectionsList(const string &variantsString, vector<SdfPath> &variants)
{
    std::vector<std::string> variantsStringTokens;
    variantsStringTokens = TfStringTokenize(variantsString, " ");
    
    for (vector<string>::iterator it = variantsStringTokens.begin();
            it != variantsStringTokens.end();
            ++it)
    {
        SdfPath path = SdfPath(*it);
        if (path.IsPrimVariantSelectionPath() )
        {
            variants.push_back(path);
        }
    }
}

MriGeoPluginResult
UsdReader::_MakeGeoEntity(
    GeoData &Geom, 
    MriGeoEntityHandle &Entity,
    string label,
    const vector<int> &frames)
{
    MriGeoDataHandle FaceVertexCounts, Vertices, Indices, UVs, UVIndices;
    MriGeoDataHandle CreaseIndices, CreaseLengths, CreaseSharpness;
    MriGeoObjectHandle Object;
    MriGeoPluginResult Result;
    CHECK_RESULT(_host.createGeoData(Entity, 
                                     Geom.GetFaceVertexCounts(), 
                                     Geom.GetNumTriangles() * sizeof(unsigned),
                                     MRI_GDT_U32_BUFFER, 
                                     MRI_GDR_MESH_FACE_VERTEX_COUNTS, 
                                     &FaceVertexCounts));
    CHECK_RESULT(_host.createGeoData(Entity, 
                                     Geom.GetVertices(), 
                                     Geom.GetNumPoints() * sizeof(float),
                                     MRI_GDT_FLOAT_BUFFER, 
                                     MRI_GDR_MESH_VERTICES, 
                                     &Vertices));
    CHECK_RESULT(_host.createGeoData(Entity, 
                                     Geom.GetIndices(), 
                                     Geom.GetNumIndices() * sizeof(unsigned int),
                                     MRI_GDT_U32_BUFFER, 
                                     MRI_GDR_MESH_VERTEX_INDICES, 
                                     &Indices));

    if (Geom.GetNumCreaseIndices() > 0)
    {
        _host.trace("setting crease lengths");
        CHECK_RESULT(_host.createGeoData(Entity, 
                                         Geom.GetCreaseLengths(),
                                         Geom.GetNumCreaseLengths() * sizeof(unsigned int),
                                         MRI_GDT_U32_BUFFER, 
                                         MRI_GDR_MESH_SUBD_CREASE_LENGTHS, 
                                         &CreaseLengths));

        _host.trace("setting crease indices %d", MRI_GDR_MESH_SUBD_CREASE_INDICES);
        CHECK_RESULT(_host.createGeoData(Entity, 
                                         Geom.GetCreaseIndices(),
                                         Geom.GetNumCreaseIndices() * sizeof(unsigned int),
                                         MRI_GDT_U32_BUFFER, 
                                         MRI_GDR_MESH_SUBD_CREASE_INDICES, 
                                         &CreaseIndices));

        _host.trace("setting crease sharpness");
        CHECK_RESULT(_host.createGeoData(Entity, 
                                         Geom.GetCreaseSharpness(),
                                         Geom.GetNumCreaseSharpness() * sizeof(float),
                                         MRI_GDT_FLOAT_BUFFER, 
                                         MRI_GDR_MESH_SUBD_CREASE_SHARPNESS, 
                                         &CreaseSharpness));
    }


    if(Geom.HasUVs()) {
        CHECK_RESULT(_host.createGeoData(
                         Entity, Geom.GetUVs(), Geom.GetNumFaceVertices() * 
                         2 * sizeof(float),
                         MRI_GDT_FLOAT_BUFFER, MRI_GDR_MESH_UV0, &UVs));
        CHECK_RESULT(_host.createGeoData(
                         Entity, Geom.GetUVIndices(), Geom.GetNumIndices() * 
                         sizeof(unsigned int),
                         MRI_GDT_U32_BUFFER, 
                         MRI_GDR_MESH_UV0_INDICES, 
                         &UVIndices));
    }

    // Load animated frames
    if (frames.size() > 1)
    {
        for (unsigned int i = 0; i<frames.size(); ++i)
        {
            int frame = frames[i];
            CHECK_RESULT(_host.setGeoDataForFrame(
                    Entity, Vertices, frame, Geom.GetVertices(frame),
                    Geom.GetNumPoints() * sizeof(float)));
        }
    }
    // Create geo object and add data        
    CHECK_RESULT(_host.createMeshObject(Entity, label.c_str(), 
            Geom.GetNumTriangles(), &Object));

    // Add data to geo object
    CHECK_RESULT(_host.addGeoDataToObject(Entity, Object, FaceVertexCounts));
    CHECK_RESULT(_host.addGeoDataToObject(Entity, Object, Vertices));
    CHECK_RESULT(_host.addGeoDataToObject(Entity, Object, Indices));
    if(Geom.HasUVs()) {
        CHECK_RESULT(_host.addGeoDataToObject(Entity, Object, UVs));
        CHECK_RESULT(_host.addGeoDataToObject(Entity, Object, UVIndices));
    }
    
    if (Geom.GetNumCreaseIndices() > 0)
    {
        _host.trace("Adding creases");
        CHECK_RESULT(_host.addGeoDataToObject(Entity, Object, CreaseIndices));
        CHECK_RESULT(_host.addGeoDataToObject(Entity, Object, CreaseLengths));
        CHECK_RESULT(_host.addGeoDataToObject(Entity, Object, CreaseSharpness));
    }

    return MRI_GPR_SUCCEEDED;
}





void
UsdReader::_ParseUVs(MriUserItemHandle SettingsHandle,
                           GeoData::UVSet uvs, 
                           int size)
{
    string choices = "";
    for (GeoData::UVSet::iterator it = uvs.begin(); it != uvs.end(); ++it)
    {
        stringstream oss;
        if (it->first == "map1")
        {
            // map1 should be the first and default choice
            oss << it->first << " (" << it->second << "/" <<
                size <<  ")" << endl << choices;
            choices = oss.str();
        }
        else
        {
            oss << it->first << " (" << it->second << "/" <<
                size <<  ")" << endl;
            choices += oss.str();
        }
    }
   
    MriAttributeValue UVValue;
    UVValue.m_Type = MRI_ATTR_STRING_LIST;
    UVValue.m_pString = choices.c_str();
    _host.setAttribute(SettingsHandle, "uvSet", &UVValue);
}

void
UsdReader::_GetMariAttributes(MriGeoEntityHandle &Entity,
                                    vector<int>& frames,
                                    std::string& frameString,
                                    vector<string>& requestedModelNames,
                                    vector<string>& requestedGprimNames,
                                    std::string& UVSet,
                                    vector<SdfPath>& variantSelections,
                                    bool& keepCentered,
                                    bool& includeInvisible)
{
    // detect requested UV set
    MriAttributeValue Value;
    if (_host.getAttribute(Entity, "uvSet", &Value) == MRI_UPR_SUCCEEDED)
    {
        UVSet = Value.m_pString;
        UVSet = UVSet.substr(0, UVSet.find(" "));   
// ignore comment on uvSet
    }
    _host.trace("[%s] Using uv set %s", _pluginName, UVSet.c_str());

    // detect requested frames
    if (_host.getAttribute(Entity, "frameNumbers", &Value) ==
            MRI_UPR_SUCCEEDED)
        frameString = Value.m_pString;
    _GetFrameList(frameString, frames);
    for (int iFrame = 0; iFrame<frames.size(); ++iFrame)
        _host.trace("[%s] requested frame number %i", _pluginName, 
                frames[iFrame]);

    // detect requested model name
    std::string modelNamesString;
    if (_host.getAttribute(Entity, "modelName", &Value) == MRI_UPR_SUCCEEDED)
        modelNamesString = Value.m_pString;
    requestedModelNames = TfStringTokenize(modelNamesString, ",");

    _host.trace("[%s] requested modelName %s", _pluginName,
                modelNamesString.c_str());

    // detect requested gprim names
    std::string gprimNamesString;
    if (_host.getAttribute(Entity, "gprimNames", &Value) == MRI_UPR_SUCCEEDED)
        gprimNamesString = Value.m_pString;
    requestedGprimNames = TfStringTokenize(gprimNamesString, ",");

    _host.trace("[%s] requested gprimString %s", _pluginName, 
                gprimNamesString.c_str());

    std::string variantsString;
    if (_host.getAttribute(Entity, "variants", &Value) == MRI_UPR_SUCCEEDED)
    {
        variantsString = Value.m_pString;
        _GetVariantSelectionsList(variantsString, variantSelections);
        _host.trace("[%s] Using variants %s", _pluginName, variantsString.c_str());
    }

    // detect if we want to ignore model transforms
    if( _host.getAttribute(Entity, "keepCentered", &Value) ==
        MRI_UPR_SUCCEEDED )
        keepCentered = (Value.m_Int !=0);
    if( keepCentered )
        _host.trace("[%s] Discarding model transforms.", _pluginName);

    // detect if we want to include invisible gprims
    if( _host.getAttribute(Entity, "includeInvisible", &Value) ==
        MRI_UPR_SUCCEEDED )
        includeInvisible = (Value.m_Int !=0);
    if( !includeInvisible )
        _host.trace("[%s] Discarding invisible gprims.", _pluginName);
}

void
UsdReader::_SaveMetadata(
        MriGeoEntityHandle &Entity,
        const ModelData& modelData)
{
    MriAttributeValue Value;
    Value.m_Type = MRI_ATTR_STRING;
    map<string, string> metadata = modelData.GetMetadata();
    map<string, string>::iterator it;
    _host.trace("[%s] Using metadata setAttribute (>2.0)", _pluginName);
    for (it = metadata.begin(); it!=metadata.end();++it)
    {
        Value.m_pString = it->second.c_str();
        _host.trace("[%s] setting metadata %s to %s", _pluginName, 
            it->first.c_str(), it->second.c_str());
        _host.setAttribute(Entity, it->first.c_str(), &Value);
    }
}


// _log is a vector of error and warning strings that gets appended to during the 
// Load phase.
// When we've finished loading, we write the string into a magic file that gets
// displayed by the python UsdReader UI code.
// This seems to be the easiest way to provide GUI feedback that there was
// an error while importing geometry, since we don't have access to the GUI 
// when we're loading.
// Perhaps there is a more elegant way of doing this? XXX
FILE * 
UsdReader::_OpenLogFile()
{
    string tmpDir = (getenv( "TMPDIR" )!=NULL ? getenv("TMPDIR") :
                         ".");
    string fileName = tmpDir + "/MariUsdReaderLog.txt";
    return fopen(fileName.c_str(), "w");
}

void
UsdReader::CloseLog()
{
    std::vector<std::string>::iterator it;
    FILE *f = _OpenLogFile();
    if (f) {
        for (it = _log.begin(); it != _log.end(); it++) {
            fputs(it->c_str(), f); fputs("\n", f);
        }
        fclose(f);
    }
}
