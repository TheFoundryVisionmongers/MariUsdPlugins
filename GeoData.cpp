#include "GeoData.h"
#include "pxr/base/gf/vec3d.h"
#include "pxr/base/gf/vec2f.h"

#include "pxr/base/vt/value.h"
#include "pxr/base/vt/array.h"
#include "pxr/usd/usdGeom/mesh.h"
#include "pxr/usd/usdGeom/xformCache.h"

#include <float.h>
using namespace std;
PXR_NAMESPACE_USING_DIRECTIVE

std::vector<std::string> GeoData::_requireGeomPathSubstring;
std::vector<std::string> GeoData::_ignoreGeomPathSubstring;

std::string GeoData::_requireGeomPathSubstringEnvVar = "PX_USDREADER_REQUIRE_GEOM_PATH_SUBSTR";
std::string GeoData::_ignoreGeomPathSubstringEnvVar = "PX_USDREADER_IGNORE_GEOM_PATH_SUBSTR";




//------------------------------------------------------------------------------
// GeoData implementation
//------------------------------------------------------------------------------
GeoData::GeoData(UsdPrim const &prim,
                 std::string uvSet,  // requested uvSet. If empty string, it's a ptex thing.
                 std::vector<int> frames,
                 bool keepCentered,
                 UsdPrim const &model,
                 const MriGeoReaderHost& host,
                 std::vector<std::string>& log):
    _numTriangles(0),
    _numFaceVertices(0)
{    

    /// Load UVs, check sanity and verify their level of detail (vertex or 
    /// facevarying)
    bool hasU = false, hasV = false;
    bool faceVaryingUU = false, faceVaryingVV = false;
    vector<float> uu, vv;
    VtValue uuVt, vvVt, uvVt;
    
    UsdGeomMesh   mesh(prim);
    if (uvSet.length() > 0) {
        // meshName
        TfToken uSet = TfToken("u_" + uvSet);
        TfToken vSet = TfToken("v_" + uvSet);

        if (not mesh){
            host.trace("[GeoData] Can't get uvs from non-mesh prim %s (type %s)", 
                       prim.GetPath().GetText(), prim.GetTypeName().GetText());
            log.push_back("Can't get uvs from non-mesh prim " +
                          prim.GetPath().GetName() + " of type " +
                          std::string(prim.GetTypeName().GetText()));
            return;
        }
    
        if (UsdGeomPrimvar uvgpv = mesh.GetPrimvar(TfToken(uvSet)))
        {
            SdfValueTypeName typeName      = uvgpv.GetTypeName();
            TfToken          interpolation = uvgpv.GetInterpolation();
            
            if ((interpolation == UsdGeomTokens->vertex or
                 interpolation == UsdGeomTokens->faceVarying) and
                (typeName == SdfValueTypeNames->Float2Array) and
                uvgpv.ComputeFlattened(&uvVt))
            {
                if (uvVt.IsHolding<VtVec2fArray>())
                {
                    hasU = true; hasV = true;
                    faceVaryingUU = interpolation == UsdGeomTokens->faceVarying;
                    faceVaryingVV = faceVaryingUU;
                    
                    VtVec2fArray uvArray = uvVt.Get<VtVec2fArray>();
                    uu.resize(uvArray.size());
                    vv.resize(uvArray.size());
                    for (int i = 0; i < uvArray.size(); ++i) 
                    {
                        // u is invalid if negative, more than 10 or on the
                        // boundary of a uv quadrant
                        uu[i] = uvArray[i][0];
                        vv[i] = uvArray[i][1];
                        if (uu[i] < 0.f || uu[i]>10.f || 
                            vv[i] < 0.f)
                        {
                            host.trace("[GeoData]\tdiscarding because of unsupported U or V coordinate (negative or >10 UV[%d](%f, %f) at:" 
                                       "%s", i, uu[i], vv[i], prim.GetPath().GetName().c_str());
                            if(uu[i] < 0.f)
                                log.push_back("Discarding mesh at " +
                                              prim.GetPath().GetName() +
                                              " because of negative U coordinate");
                            if(uu[i] > 10.f)
                                log.push_back("Discarding mesh at " +
                                              prim.GetPath().GetName() +
                                              " because of U coordinate greater than 10");
                            if(vv[i] < 0.f)
                                log.push_back("Discarding mesh at " +
                                              prim.GetPath().GetName() +
                                              " because of negative V coordinate");
                            return;
                        }
                    }
                }
            } else {
                host.trace("[GeoData]\tDiscarding because Vertex or Facevarying "
                           "interpolation is not defined for the \"%s\" uv set on "
                           "%s.", uvSet.c_str(), prim.GetPath().GetName().c_str());
                log.push_back("Discarding because Vertex or Facevarying interpolation is not defined for uvset" +
                              std::string(uvSet) + " on gprim " +
                              std::string(prim.GetPath().GetName()));
                return;
            }
        } else {
        
            if (UsdGeomPrimvar ugpv = mesh.GetPrimvar(uSet))
            {
                SdfValueTypeName typeName      = ugpv.GetTypeName();
                TfToken          interpolation = ugpv.GetInterpolation();

                if ((interpolation == UsdGeomTokens->vertex or
                     interpolation == UsdGeomTokens->faceVarying) and
                    (typeName == SdfValueTypeNames->FloatArray) and
                    ugpv.ComputeFlattened(&uuVt))
                {
                    hasU = true;
                    faceVaryingUU = interpolation == UsdGeomTokens->faceVarying;
                }
            }

            if (UsdGeomPrimvar vgpv = mesh.GetPrimvar(vSet))
            {
                SdfValueTypeName typeName       = vgpv.GetTypeName();
                TfToken          interpolation = vgpv.GetInterpolation();

                if ((interpolation == UsdGeomTokens->vertex or
                     interpolation == UsdGeomTokens->faceVarying) and
                    (typeName == SdfValueTypeNames->FloatArray) and
                    vgpv.ComputeFlattened(&vvVt))
                {
                    hasV = true;
                    faceVaryingVV = interpolation == UsdGeomTokens->faceVarying;
                }
            }

            // No uvs, this is only good for ptex, and we asked for a uvSet. So discard.
            if (!(hasU && hasV)) 
            {
                host.trace("[GeoData] Couldn't find uvset data on %s", 
                           prim.GetPath().GetText());
                return; // this is not optional!
            }

            if (uuVt.IsHolding<VtFloatArray>())
            {
                VtFloatArray uuArray = uuVt.Get<VtFloatArray>();
                for (int i = 0; i < uuArray.size(); ++i) 
                {
                    // u is invalid if negative or more than 10 
                    float u = uuArray[i];
                    if (u < 0.f || u>10.f) 
                    {
                        host.trace("[GeoData]\tdiscarding %s because of bad U coordinates (%f) at index %i",
                            prim.GetPath().GetName().c_str(), u, i);
                        if (u < 0.f) 
                            log.push_back("Discarding " + prim.GetPath().GetName() +
                                          " because of negative U coordinates");
                        if (u > 10.f) 
                            log.push_back("Discarding " + prim.GetPath().GetName() +
                                          " because of U coordinates greater than 10.");
                        return;
                    }
                }
                uu = vector<float>(uuArray.begin(), uuArray.end());
            } 
            else 
            {
                return;
            }

            if (vvVt.IsHolding<VtFloatArray>()) 
            {
                VtFloatArray vvArray = vvVt.Get<VtFloatArray>();
                for (int i = 0; i < vvArray.size(); ++i) 
                {
                    float v = vvArray[i];
                    if (v < 0.f) 
                    {
                        host.trace("[GeoData]\tdiscarding %s because of bad V coordinates (%f) at index %i",
                            prim.GetPath().GetName().c_str(), v, i);
                        log.push_back("Discarding " + prim.GetPath().GetName() +
                                      " because of negative V coordinates.");
                        return;
                    }
                }
                vv = vector<float>(vvArray.begin(), vvArray.end());
            } 
            else 
            {
                return;
            }
        }
    }

    _selectionGroupName = prim.GetParent().GetPath().GetName();

    ////////////
    /// TOPOLOGY
    ///
    VtIntArray vertsIndicesArray, nvertsPerFaceArray, creaseIndicesArray, 
        creaseLengthsArray;
    VtFloatArray creaseSharpnessArray;

    if (!mesh.GetFaceVertexIndicesAttr().Get(&vertsIndicesArray)) 
    {
        host.trace("[GeoData]\tfailed getting faces on %s.",
                prim.GetPath().GetName().c_str());
        log.push_back("Failed getting faces on " +
                      prim.GetPath().GetName());
        return;// this is not optional!
    }
    vector<int> vertsIndices(vertsIndicesArray.begin(), 
            vertsIndicesArray.end());

    if (!mesh.GetFaceVertexCountsAttr().Get(&nvertsPerFaceArray)) 
    {
        host.trace("[GeoData]\tfailed getting faces on %s",
                prim.GetPath().GetName().c_str());
        log.push_back("Failed getting faces on " +
                      prim.GetPath().GetName());
        return;// this is not optional!
    }
    vector<int> nvertsPerFace(nvertsPerFaceArray.begin(), 
            nvertsPerFaceArray.end());

    if (!mesh.GetCreaseIndicesAttr().Get(&creaseIndicesArray))
    {
        host.trace("[GeoData]\tfailed getting creases on %s",
                prim.GetPath().GetName().c_str());
    }

    _creaseIndices = vector<int>(creaseIndicesArray.begin(), 
                                 creaseIndicesArray.end());

    host.trace("creaseIndices.size() => %d", _creaseIndices.size());
    if (_creaseIndices.size() > 0)
    {
        if (!mesh.GetCreaseLengthsAttr().Get(&creaseLengthsArray))
        {
            host.trace("[GeoData]\tfailed getting crease lengths on %s",
                       prim.GetPath().GetName().c_str());
        }
        _creaseLengths = vector<int>(creaseLengthsArray.begin(), 
                                     creaseLengthsArray.end());

        if (!mesh.GetCreaseSharpnessesAttr().Get(&creaseSharpnessArray))
        {
            host.trace("[GeoData]\tfailed getting crease sharpness on %s",
                       prim.GetPath().GetName().c_str());
        }
        _creaseSharpness = vector<float>(creaseSharpnessArray.begin(), 
                                         creaseSharpnessArray.end());
    }

    // process indices to something mari understands:
    // triangulate and turn everything into facevarying
    int totalPointCount = 0;
    vector<float> points;

    unsigned int nFaces = nvertsPerFace.size();
    TfToken orientation;
    bool leftHandedness = false;

    // If any uu or vv values are on integer values, nudge them in to be in
    // the same span as the rest of the values on the face in question.
    if (uvSet.length() > 0) {
        _NudgeUVs(uu, vv, vertsIndices, nvertsPerFace, host);
    }

    // Get handedness
    if (mesh.GetOrientationAttr().Get(&orientation)) 
    {
        if( orientation == UsdGeomTokens->leftHanded ) 
        {
            leftHandedness = true;
        }
        else 
        {
            leftHandedness = false;
        }
    }


    ////////////
    /// ANIMATED DATA:
    ///     VERTICES
    ///
    for (unsigned int iFrame = 0; iFrame < frames.size(); ++iFrame) 
    {
        unsigned int frame = frames[iFrame];
        host.trace("[GeoData]\tProcessing frame %i: %i", iFrame, frame);
        double currentTime = double(frame);

        VtVec3fArray pointsVt;
        if (!mesh.GetPointsAttr().Get(&pointsVt, frame)) 
        {
            host.trace("[GeoData]\tfailed getting faces on %s.",
                       prim.GetPath().GetName().c_str());
            log.push_back("Failed getting faces on " +
                          prim.GetPath().GetName());
            return;// this is not optional!
        }
        
        points.resize(pointsVt.size() * 3);
        for(int i = 0; i < pointsVt.size(); ++i) 
        {
            points[i * 3    ] = pointsVt[i][0];
            points[i * 3 + 1] = pointsVt[i][1];
            points[i * 3 + 2] = pointsVt[i][2];
        }

        if (iFrame == 0) 
        {
            // only once
            host.trace("[GeoData]\t%i U uvSet count", uu.size());
            host.trace("[GeoData]\t%i V uvSet count", vv.size());
            host.trace("[GeoData]\t%i vertices", points.size());
            host.trace("[GeoData]\tTopology was computed. Allocating space for"
                    "arrays.");
            host.trace("[GeoData]\t\t%i faces", nFaces);
            host.trace("[GeoData]\t\t%i indices", vertsIndices.size());

            // estimate sizes and reserve space for arrays
            for (unsigned int iFace = 0; iFace < nFaces; ++iFace)
                // 3 points per triangle
                totalPointCount += nvertsPerFace[iFace];
            _indices.reserve(totalPointCount);
            _uvIndices.reserve(totalPointCount);
            // 2 floats per uv
            if (uvSet.length() > 0) {
                _uvs.resize(totalPointCount*2);
            }
        }



        // allocate space on vertices, same value on each frame
        // 3 floats per point
        host.trace("[GeoData]\tAllocating space for vertices.");
        _vertices[frame].resize(points.size());

        // calculate transforms.
        // if not identity, pre-transform all points in place
        GfMatrix4d const IDENTITY(1);
        UsdGeomXformCache xformCache(currentTime);
        GfMatrix4d fullXform = xformCache.GetLocalToWorldTransform(prim);

        if (keepCentered)
        {
            // ignore transforms up to the model level
            GfMatrix4d m = xformCache.GetLocalToWorldTransform(model);
            fullXform = m.GetInverse() * fullXform;
        }
                
        if (fullXform != IDENTITY)
        {
            host.trace("\tTransforming points...");
            int psize = points.size();
            for (unsigned int iPoint = 0; iPoint < psize; iPoint += 3)
            {
                GfVec4d p (points[iPoint    ],
                           points[iPoint + 1],
                           points[iPoint + 2],1.0);
                p = p * fullXform;
                points[iPoint    ] = p[0];
                points[iPoint + 1] = p[1];
                points[iPoint + 2] = p[2];
            }
        }

        ////////////
        ///  COPY ALL THE DATA INTO THE MARI COMPATIBLE STRUCTURES
        ///
        host.trace("[GeoData]\tTransfering data to mari-compatible structures");
        _BuildMariGeoData(frame,
                          iFrame,
                          nFaces, 
                          leftHandedness,
                          nvertsPerFace,
                          points,
                          vertsIndices,
                          uvSet,
                          faceVaryingUU,
                          faceVaryingVV,
                          uu,
                          vv,
                          host);

    }

    _CalculateFaceIndices();
}


void
GeoData::_CalculateFaceIndices() 
{
    // set up faceindices for selection sets. It is basically 
    // all faces of this prim, since that's what mari expects.
    _faceIndices.resize(_numTriangles);
    for (int iFaceIndex = 0; iFaceIndex<_numTriangles; ++iFaceIndex)
        _faceIndices[iFaceIndex] = iFaceIndex;
}

void
GeoData::_BuildMariGeoData(const int frame,
                           const int iFrame,
                           const int nFaces,
                           const bool leftHandedness,
                           const vector<int>& nvertsPerFace,
                           const vector<float>& points,
                           const vector<int>& vertIndices,
                           const string& uvSet,
                           const bool faceVaryingUU,
                           const bool faceVaryingVV,
                           const vector<float>& uu,
                           const vector<float>& vv,
                           const MriGeoReaderHost& host)
{
    set<int> vertsAdded;
    unsigned int nVertsOnThisFace;
    unsigned int iIndexFaceVaryingBase = 0;
    unsigned int iIndexFaceVarying;
    unsigned int indexVertex;
    
    for (unsigned int iFace = 0; iFace < nFaces; ++iFace) 
    {
        // host.trace("Face %i", iFace);
        nVertsOnThisFace = nvertsPerFace[iFace];
        
        for (unsigned int iVert = 0; iVert < nVertsOnThisFace; ++iVert) 
        {
            iIndexFaceVarying = iIndexFaceVaryingBase;
            if (iVert > 0)
            {
                if (leftHandedness)
                {
                    // invert 1 and 2
                    iIndexFaceVarying += nVertsOnThisFace - iVert;
                }
                else
                    iIndexFaceVarying += iVert;
            }

            if (iIndexFaceVarying >= vertIndices.size())
            {
                // host.trace("\t\t\tskip");
                continue;
            }

            indexVertex = vertIndices[iIndexFaceVarying];

            if (indexVertex < 0 || indexVertex >= points.size()) {
                // host.trace("\t\t\t\tbad! force to 0");
                indexVertex = 0;
            }

            if (vertsAdded.find(indexVertex) == vertsAdded.end())
            {
                // vertex, changes per frame
                // Convert Z-up to Y-up
                _vertices[frame][indexVertex * 3] = 
                    points[indexVertex * 3    ]; // x
                _vertices[frame][indexVertex * 3 + 1] = 
                    points[indexVertex * 3 + 2]; // y
                _vertices[frame][indexVertex * 3 + 2] = 
                    -points[indexVertex * 3 + 1]; // z
            }
                
            // only assign topology and UVs for the first frame
            if (iFrame == 0)
            {
                _numFaceVertices++;
                _indices.push_back(indexVertex);
                
                // uvs
                if(uvSet.length() > 0) {
                    _uvs[iIndexFaceVarying*2] =
                        uu[faceVaryingUU ? iIndexFaceVarying : indexVertex];
                    _uvs[iIndexFaceVarying*2+1] = 
                        vv[faceVaryingVV ? iIndexFaceVarying : indexVertex];
                    _uvIndices.push_back(iIndexFaceVarying);                    
                }
            }
        }
        iIndexFaceVaryingBase+=nVertsOnThisFace;
        if (iFrame == 0)
        {
            _numTriangles++;
            _vertsPerFace.push_back(nVertsOnThisFace);
        }
    }

}

GeoData::~GeoData()
{
    Reset();
}


// Print the internal status of the Geometric Data.
void
GeoData::Log(const MriGeoReaderHost& host)
{
    host.trace("Resulting mari mesh: ");
    host.trace("\tVertex Array Length: %i floats (%i points)", 
        _vertices.begin()->second.size(), _vertices.begin()->second.size()/3);
    host.trace("\tIndex Array Length: %i", _indices.size());
    host.trace("\tUV Array Length: %i floats (%i uvs)", 
        _uvs.size(), _uvs.size()/2);
    host.trace("\tNumTriangles: %i", _numTriangles);
    host.trace("\tNumCorners: %i", _numFaceVertices);
}


// Cast to bool. False if no good data is found.
GeoData::operator bool()
{
    return (_vertices.size() > 0 && 
        _vertices.begin()->second.size()>0 && 
        _indices.size()>0);
}


void
GeoData::GetSelectionGroup(string& name, int & size, int*& faceIndices) 
{
    size = _numTriangles;
    name = _selectionGroupName;
    faceIndices = &(_faceIndices[0]);
}


// Static - Sanity test to see if the usd prim is something we can use.
bool
GeoData::IsValidNode(UsdPrim const &prim)
{
    if (not prim.IsA<UsdGeomMesh>())
        return false;
    else
        return TestPath( prim.GetPath().GetText());
}



// Pre-scan the UsdStage to see what uv sets are included.
void
GeoData::GetUvSets(UsdPrim const &prim, UVSet &retval)
{
    UsdGeomGprim   gprim(prim);
    if (not gprim)
        return;

    vector<UsdGeomPrimvar> primvars = gprim.GetPrimvars();
    TF_FOR_ALL(primvar, primvars) 
    {
        TfToken          name, interpolation;
        SdfValueTypeName typeName;
        int              elementSize;

        primvar->GetDeclarationInfo(&name, &typeName, 
                                     &interpolation, &elementSize);
        
        if (interpolation == UsdGeomTokens->vertex or
             interpolation == UsdGeomTokens->faceVarying)
        {
            string prefix = name.GetString().substr(0,2);
            string mapName("");
        
            if ((prefix == "v_" || prefix == "u_") and
                (typeName == SdfValueTypeNames->FloatArray))
            {
                mapName = name.GetString().substr(2);
            } else if (typeName == SdfValueTypeNames->Float2Array)
            {
                mapName = name.GetString();
            }
            if (mapName.length()) {
                UVSet::iterator it = retval.find(mapName);
                if (it == retval.end())
                    retval[mapName] = 1;
                else
                    retval[mapName] += 1;
            }
        }
    }
}

float* 
GeoData::GetVertices(int frame)
{
    if (_vertices.size() > 0)
    {
        if (frame == -1)
            // no frame specified. Return first found...
            return &(_vertices.begin()->second[0]);
        else
        {
            // some frame requested. Return it if found
            if (_vertices.find(frame) != _vertices.end())
                return &(_vertices[frame][0]);
        }
    }

    // frame not found.
    return NULL;
}


void
GeoData::Reset()
{
    _numTriangles = 0;
    _numFaceVertices = 0;
}



bool
GeoData::TestPath(string path) 
{
    bool requiredSubstringFound = true;
    std::vector<std::string>::iterator i;
    for (i=_requireGeomPathSubstring.begin(); i!=_requireGeomPathSubstring.end(); ++i)
    {
        if (path.find(*i) != string::npos)
        {
            requiredSubstringFound = true;
            break;
        } else {
            requiredSubstringFound = false;
        }
    }

    if (requiredSubstringFound == false) 
    {
        return false;
    }

    for (i=_ignoreGeomPathSubstring.begin(); i!=_ignoreGeomPathSubstring.end(); ++i)
    {
        if (path.find(*i) != string::npos)
        {
            return false;
        }
    }
    return true;
}
    

void
GeoData::InitializePathSubstringLists() 
{
    char * ignoreEnv = getenv(_ignoreGeomPathSubstringEnvVar.c_str());
    char * requireEnv = getenv(_requireGeomPathSubstringEnvVar.c_str());
    
    if (ignoreEnv) 
    {
        _ignoreGeomPathSubstring.clear();
        _ignoreGeomPathSubstring = TfStringTokenize(ignoreEnv, ",");
    }

    if (requireEnv) 
    {
        _requireGeomPathSubstring.clear();
        _requireGeomPathSubstring = TfStringTokenize(requireEnv, ",");
    }
}

template <typename SOURCE, typename TYPE>
bool
GeoData::CastVtValueAs(SOURCE &obj, TYPE &result)
{
    if ( obj.template CanCast<TYPE>() ) 
    {
        obj = obj.template Cast<TYPE>();
        result = obj.template Get<TYPE>();
        return true;
    }
    return false;
}

void
GeoData::_NudgeUVs(
    vector<float>& u, 
    vector<float>& v,
    const vector<int>& vertsIndices,
    const vector<int>& numVertsPerFace,
    const MriGeoReaderHost& host)
{
    // Loop over all Faces
    for( int i = 0, j = 0; i < numVertsPerFace.size(); j+=numVertsPerFace[i], i++)
    {
        float offset = 0.f;
        float epsilon = 5.f * FLT_EPSILON;
        // Loop over all vertices in the face.
        for (int k = 0; k < numVertsPerFace[i]; ++k)
        {
            int iVertex = vertsIndices[j+k];

            // Is the u value on this vertex on an integer boundary?
            if (floorf(u[iVertex]) == u[iVertex]) {
                // If so compare it with the u values on the other
                // vertices of this face and nudge it into the 
                // span of the rest of them.
                // e.g. If the vertex in question is 3.0
                // and another vertex has 3.3, we'll 
                // add 5*FLT_EPSLION. If another vertex is
                // 2.8, we'll subtract 5*FLT_EPSILON.
                
                offset = 0.f;
                for(int m = 0; m < numVertsPerFace[i]; ++m)
                {
                    if (m == k) continue;

                    int iOtherVertex = vertsIndices[j+m];
                    
                    if (u[iVertex] > u[iOtherVertex])
                    {
                        offset = -epsilon;
                        break;
                    }
                    if (u[iVertex] < u[iOtherVertex])
                    {
                        offset = epsilon;
                        break;
                    }
                }
                u[iVertex] += offset;
            }          
            // Now repeat for v values on this vertex.
            if (floorf(v[iVertex]) == v[iVertex]) {
                offset = 0.f;
                for(int m = 0; m < numVertsPerFace[i]; ++m)
                {
                    if (m == k) continue;

                    int iOtherVertex = vertsIndices[j+m];
                    
                    if (v[iVertex] > v[iOtherVertex])
                    {
                        offset = -epsilon;
                        break;
                    }
                    if (v[iVertex] < v[iOtherVertex])
                    {
                        offset = epsilon;
                        break;
                    }
                }
                v[iVertex] += offset;
            }          
        }
    }
}


