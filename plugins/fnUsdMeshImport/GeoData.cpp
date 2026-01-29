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

#include "GeoData.h"
#include "pxr/base/gf/vec3d.h"
#include "pxr/base/gf/vec2f.h"

#include "pxr/base/vt/value.h"
#include "pxr/base/vt/array.h"
#include "pxr/base/tf/envSetting.h"
#include "pxr/usd/usdGeom/mesh.h"
#include "pxr/usd/usdGeom/xformCache.h"
#include "pxr/usd/usdGeom/primvarsAPI.h"
#include "pxr/usd/sdf/path.h"
#include "pxr/usd/sdf/payload.h"
#include "pxr/usd/sdf/reference.h"

#include <algorithm>
#include <float.h>

PXR_NAMESPACE_USING_DIRECTIVE

TF_DEFINE_ENV_SETTING(MARI_READ_FLOAT2_AS_UV, true,
        "Set to false to disable ability to read Float2 type as a UV set");

std::vector<std::string> GeoData::_requireGeomPathSubstring;
std::vector<std::string> GeoData::_ignoreGeomPathSubstring;

std::string GeoData::_requireGeomPathSubstringEnvVar = "PX_USDREADER_REQUIRE_GEOM_PATH_SUBSTR";
std::string GeoData::_ignoreGeomPathSubstringEnvVar = "PX_USDREADER_IGNORE_GEOM_PATH_SUBSTR";

//------------------------------------------------------------------------------
// GeoData implementation
//------------------------------------------------------------------------------

bool GeoData::ReadFloat2AsUV()
{
    static const bool readFloat2AsUV =
        TfGetEnvSetting(MARI_READ_FLOAT2_AS_UV);
    return readFloat2AsUV;
}

GeoData::GeoData(UsdPrim const &prim,
                 std::string uvSet,
                 std::string mappingScheme,
                 std::vector<int> frames,
                 bool conformToMariY,
                 bool readerIsUpY,
                 bool keepCentered,
                 UsdPrim const &model,
                 const PluginHosts* pluginHosts,
                 std::vector<std::string>& log,
                 bool rightHandedWindingOrder)
{
    // Init
    m_isSubdivMesh = false;
    m_subdivisionScheme = "";
    m_interpolateBoundary = 0;
    m_faceVaryingLinearInterpolation = 0;
    m_propagateCorner = 0;
    m_triangleSubdivision = 0;
    m_isRightHandWindingOrder = rightHandedWindingOrder;

    UsdGeomMesh mesh(prim);
    if (not mesh)
    {
        pluginHosts->geoReaderHost.trace("[GeoData:%d] Invalid non-mesh prim %s (type %s)", __LINE__, prim.GetPath().GetText(), prim.GetTypeName().GetText());
        log.push_back("** Invalid non-mesh prim " + std::string(prim.GetPath().GetText()) + " of type " + std::string(prim.GetTypeName().GetText()));
        return;
    }

    bool isTopologyVarying = mesh.GetFaceVertexIndicesAttr().GetNumTimeSamples() >= 1;

    // Read vertex/face indices
    {
        VtIntArray vertsIndicesArray;
        bool ok = isTopologyVarying ? mesh.GetFaceVertexIndicesAttr().Get(&vertsIndicesArray, UsdTimeCode::EarliestTime()) : mesh.GetFaceVertexIndicesAttr().Get(&vertsIndicesArray);
        if (!ok)
        {
            pluginHosts->geoReaderHost.trace("[GeoData:%d]\tfailed getting face vertex indices on %s.", __LINE__, prim.GetPath().GetText());
            log.push_back("** Failed getting faces on " + std::string(prim.GetPath().GetText()));
            return;// this is not optional!
        }
        m_vertexIndices = std::vector<int>(vertsIndicesArray.begin(), vertsIndicesArray.end());
    }

    // Read face counts
    {
        VtIntArray nvertsPerFaceArray;
        bool ok = isTopologyVarying ? mesh.GetFaceVertexCountsAttr().Get(&nvertsPerFaceArray, UsdTimeCode::EarliestTime()) : mesh.GetFaceVertexCountsAttr().Get(&nvertsPerFaceArray);
        if (!ok)
        {
            pluginHosts->geoReaderHost.trace("[GeoData:%d]\tfailed getting face counts on %s", __LINE__, prim.GetPath().GetText());
            log.push_back("** Failed getting faces on " + std::string(prim.GetPath().GetText()));
            return;// this is not optional!
        }
        m_faceCounts = std::vector<int>(nvertsPerFaceArray.begin(), nvertsPerFaceArray.end());
    }

    // Create face selection indices
    {
        m_faceSelectionIndices.reserve(m_faceCounts.size());
        for(auto x = 0u; x < m_faceCounts.size(); ++x)
        {
            m_faceSelectionIndices.push_back(x);
        }
    }

    UsdGeomPrimvarsAPI meshPrimApi(mesh);

    if (mappingScheme != "Force Ptex")
    {
        if ((mappingScheme == "Force empty") || // Force all UVs to be zero or...
            (uvSet.empty() && mappingScheme == "UV if available, empty otherwise")) // ...allowing empty UVs and it has none.
        {
            // Set all UVs to zero.
            m_uvs.resize(2);
            m_uvs[0] = 0.0f;
            m_uvs[1] = 0.0f;
            
            m_uvIndices = std::vector<int>(m_vertexIndices.size(), 0);
        }
        else if (!uvSet.empty())
        {
            // Get UV set primvar
            if (UsdGeomPrimvar uvPrimvar = meshPrimApi.GetPrimvar(TfToken(uvSet)))
            {
                SdfValueTypeName typeName      = uvPrimvar.GetTypeName();
                TfToken          interpolation = uvPrimvar.GetInterpolation();

                if ((interpolation == UsdGeomTokens->faceVarying or interpolation == UsdGeomTokens->vertex) and (typeName == SdfValueTypeNames->TexCoord2fArray or (GeoData::ReadFloat2AsUV() and typeName == SdfValueTypeNames->Float2Array)))
                {
                    VtVec2fArray values;
                    VtIntArray indices;
                    if (uvPrimvar.Get(&values, UsdTimeCode::EarliestTime()))
                    {
                        // Read uvs
                        m_uvs.resize(values.size()*2);
                        for (auto i = 0u; i < values.size(); ++i)
                        {
                            m_uvs[i * 2    ] = values[i][0];
                            m_uvs[i * 2 + 1] = values[i][1];
                        }

                        // Get indices
                        bool ok = isTopologyVarying ? uvPrimvar.GetIndices(&indices, UsdTimeCode::EarliestTime()) : uvPrimvar.GetIndices(&indices);
                        if (ok)
                        {
                            if (interpolation == UsdGeomTokens->faceVarying)
                            {
                                // All good -> primvar is indexed: validate/process values and indices together
                                m_uvIndices = std::vector<int>(indices.begin(), indices.end());
                            }
                            else
                            {
                                // vertex interpolated -> do extra extrapolation
                                m_uvIndices.reserve(m_vertexIndices.size());

                                // To build an actual face varying uv indices array, we need to
                                // 1. for each vertex V on a face F, get its vertex index V from the vertexIndices array
                                // 2. use VI as an index into the original vertex-interpolcated uv index table, to get uv index UVI
                                // 3. add UVI to final face varying uv index array
                                // VITAL NOTE: the final uv indices array count MUST MATCH the vertex indices array count
                                std::vector<int> UvIndices = std::vector<int>(indices.begin(), indices.end());
                                int globalIndex = 0;
                                for(auto x = 0u; x < m_faceCounts.size(); ++x)
                                {
                                    int vertCount = m_faceCounts[x];
                                    for (int vertIndex = 0; vertIndex < vertCount; ++vertIndex)
                                    {
                                        int vertId = m_vertexIndices[globalIndex++];

                                        int uvId = UvIndices[vertId];
                                        m_uvIndices.push_back(uvId);
                                    }
                                }
                            }
                        }
                        else
                        {
                            // Our uvs are not indexed -> we need to fill in an ordered list of indices
                            m_uvIndices.reserve(m_vertexIndices.size());
                            for (unsigned int x = 0; x < m_vertexIndices.size(); ++x)
                            {
                                m_uvIndices.push_back(x);
                            }
                        }
                    }
                    else
                    {
                        // Could not read uvs
                        pluginHosts->geoReaderHost.trace("[GeoData:%d]\tDiscarding mesh %s - specified uv set %s cannot be read", __LINE__, prim.GetPath().GetText(), uvSet.c_str());
                        log.push_back("** Discarding mesh " + std::string(prim.GetPath().GetText()) + " - specified uv set " + uvSet + " cannot be read");
                        return;
                    }
                }
                else
                {
                    // Incorrect interpolation
                    pluginHosts->geoReaderHost.trace("[GeoData:%d]\tDiscarding mesh %s - specified uv set %s is not of type 'faceVarying or vertex'", __LINE__, prim.GetPath().GetText(), uvSet.c_str());
                    log.push_back("** Discarding mesh " + std::string(prim.GetPath().GetText()) + " - specified uv set " + uvSet + " is not of type 'faceVarying or vertex'");
                    return;
                }
            }
            else
            {
                // UV set not found on mesh
                pluginHosts->geoReaderHost.trace("[GeoData:%d]\tSpecified uv set %s not found on mesh %s - will use ptex", __LINE__, uvSet.c_str(), prim.GetPath().GetText());
                log.push_back("** Discarding mesh " + std::string(prim.GetPath().GetText()) + " - specified uv set " + uvSet + " not found");
            }
        }
    }
    else
    {
        // Mari will use Ptex for uv-ing later on
    }

    // Read normals
    {
        VtVec3fArray normalsVt;
        VtIntArray indices;
        TfToken interpolation;
        bool ok = false;
        if (UsdGeomPrimvar normalsPrimvar = meshPrimApi.GetPrimvar(UsdGeomTokens->normals))
        {
            // Normals primvar takes precedence over normals attribute.

            ok = normalsPrimvar.Get(&normalsVt, UsdTimeCode::EarliestTime());
            if (ok)
            {
                // Get the index list from the primvar.
                ok = isTopologyVarying ? normalsPrimvar.GetIndices(&indices, UsdTimeCode::EarliestTime()) : normalsPrimvar.GetIndices(&indices);
            }

            interpolation = normalsPrimvar.GetInterpolation();
        }
        else
        {
            // No primvar, pull the attribute.

            ok = isTopologyVarying ? mesh.GetNormalsAttr().Get(&normalsVt, UsdTimeCode::EarliestTime()) : mesh.GetNormalsAttr().Get(&normalsVt);

            interpolation = mesh.GetNormalsInterpolation();
        }

        if (ok)
        {
            if ((interpolation == UsdGeomTokens->faceVarying) || (interpolation == UsdGeomTokens->vertex))
            {
                const size_t numNormals = normalsVt.size();

                // Generate a list of indices to use if an explicit list was not specified.
                if (indices.empty())
                {
                    // TP-524982 - Slightly convoluted but some files have as many vertex normals as there are vertices
                    //             and some have as many as there are vertex indices. When mapping normals to vertices
                    //             in a 1:1 fashion, we need to make sure they match up.

                    // First we find out what the maximum vertex index is.
                    // Note: This is not the same as the number of indices.
                    int maxVertexIndex = 0;
                    for (const int &vertexIndex : m_vertexIndices)
                    {
                        if (vertexIndex > maxVertexIndex)
                            maxVertexIndex = vertexIndex;
                    }

                    const int numVertIndices = static_cast<int>(m_vertexIndices.size());

                    indices.reserve(numVertIndices);

                    if (numNormals == static_cast<size_t>(maxVertexIndex)+1)
                    {
                        // In the case where there are as many normals as there are vertices
                        // we'll match up the normal indices to the vertex indices.
                        for (int x = 0; x < numVertIndices; ++x)
                        {
                            indices.push_back(m_vertexIndices[x]);
                        }
                    }
                    else
                    {
                        // In the case where there are as many normals as there are vertex
                        // indices, we'll just use a linear list.
                        for (int x = 0; x < numVertIndices; ++x)
                        {
                            indices.push_back(x);
                        }
                    }
                }

                // Extract the normal vectors.
                m_normals.reserve(numNormals * 3);
                for (const GfVec3f& normal : normalsVt)
                {
                    m_normals.push_back(normal[0]);
                    m_normals.push_back(normal[1]);
                    m_normals.push_back(normal[2]);
                }

                // Handle the normal indices.
                if (interpolation == UsdGeomTokens->faceVarying)
                {
                    // For face varying, we can take the index list as-is.
                    m_normalIndices = std::vector<int>(indices.begin(), indices.end());
                }
                else if (interpolation == UsdGeomTokens->vertex)
                {
                    // For vertex interpolated, handle it in the same manner as the UVs above.
                    m_normalIndices.reserve(m_vertexIndices.size());

                    int globalIndex = 0;
                    for (const int vertCount : m_faceCounts)
                    {
                        for (int vertIndex = 0; vertIndex < vertCount; ++vertIndex)
                        {
                            const int vertId = m_vertexIndices[globalIndex++];

                            const int uvId = indices[vertId];
                            m_normalIndices.push_back(uvId);
                        }
                    }
                }
            }
            else
            {
                // UV set not found on mesh
                pluginHosts->geoReaderHost.trace("[GeoData:%d]\tVertex normals for mesh %s are not interpolated as 'vertex' or 'faceVarying', ignoring them.", __LINE__, prim.GetPath().GetText());
                log.push_back("** Vertex normals for mesh " + std::string(prim.GetPath().GetText()) + " are not interpolated as 'vertex' or 'faceVarying', ignoring them.");
            }
        }
    }

    // Load vertices and animation frames
    GfMatrix4d const IDENTITY(1);
    std::vector<float> points;
    for (unsigned int iFrame = 0; iFrame < frames.size(); ++iFrame) 
    {
        // Get frame sample corresponding to frame index
        unsigned int frameSample = frames[iFrame];
        double currentTime = double(frameSample);

        // Read points for this frame sample
        VtVec3fArray pointsVt;
        if (!mesh.GetPointsAttr().Get(&pointsVt, frameSample))
        {
            pluginHosts->geoReaderHost.trace("[GeoData:%d]\tfailed getting vertices on %s.", __LINE__, prim.GetPath().GetName().c_str());
            log.push_back("** Failed getting faces on " + prim.GetPath().GetName());
            return;// this is not optional!
        }
        
        points.resize(pointsVt.size() * 3);
        for(auto i = 0u; i < pointsVt.size(); ++i) 
        {
            points[i * 3    ] = pointsVt[i][0];
            points[i * 3 + 1] = pointsVt[i][1];
            points[i * 3 + 2] = pointsVt[i][2];
        }

        // Calculate transforms - if not identity, pre-transform all points in place
        UsdGeomXformCache xformCache(currentTime);
        GfMatrix4d fullXform(1.0);

        if (keepCentered)
        {
            // ignore transforms up to the model level
            GfMatrix4d m = xformCache.GetLocalToWorldTransform(model);
            fullXform = m.GetInverse();
        }
        else
        {
            fullXform = xformCache.GetLocalToWorldTransform(prim);
        }

        if (fullXform != IDENTITY)
        {
            auto psize = points.size();
            for (auto iPoint = 0u; iPoint < psize; iPoint += 3)
            {
                GfVec4d p(points[iPoint], points[iPoint + 1], points[iPoint + 2], 1.0);
                p = p * fullXform;
                points[iPoint    ] = static_cast<float>(p[0]);
                points[iPoint + 1] = static_cast<float>(p[1]);
                points[iPoint + 2] = static_cast<float>(p[2]);
            }

            // TODO: Do we need to rotate normals (and tangents/bitangents) as well?
        }

        if (conformToMariY && !readerIsUpY)
        {
            // Our source is Z and we need to conform to Y -> let's flip
            auto psize = points.size();
            for (auto iPoint = 0u; iPoint < psize; iPoint += 3)
            {
                float y = points[iPoint + 1];
                points[iPoint + 1] = points[iPoint + 2];
                points[iPoint + 2] = -y;
            }

            // TODO: Do we need to rotate normals (and tangents/bitangents) as well?
        }

        if (keepCentered)
        {
            GfVec3f minExtents(std::numeric_limits<float>::max());
            GfVec3f maxExtents(std::numeric_limits<float>::min());

            const auto psize = points.size();
            for (auto iPoint = 0u; iPoint < psize; iPoint += 3)
            {
                const float px = points[iPoint];
                const float py = points[iPoint+1];
                const float pz = points[iPoint+2];
                if (keepCentered)
                {
                    minExtents[0] = std::min(px, minExtents[0]);
                    minExtents[1] = std::min(py, minExtents[1]);
                    minExtents[2] = std::min(pz, minExtents[2]);

                    maxExtents[0] = std::max(px, maxExtents[0]);
                    maxExtents[1] = std::max(py, maxExtents[1]);
                    maxExtents[2] = std::max(pz, maxExtents[2]);
                }
            }

            const float offsetX = minExtents[0] + (maxExtents[0] - minExtents[0]) * 0.5f;
            const float offsetY = minExtents[1] + (maxExtents[1] - minExtents[1]) * 0.5f;
            const float offsetZ = minExtents[2] + (maxExtents[2] - minExtents[2]) * 0.5f;

            if ((offsetX != 0.0f) || (offsetY != 0.0f) || (offsetZ != 0.0f))
            {
                for (unsigned int iPoint = 0; iPoint < psize; iPoint += 3)
                {
                    points[iPoint]   -= offsetX;
                    points[iPoint+1] -= offsetY;
                    points[iPoint+2] -= offsetZ;
                }
            }
        }

        // Insert transformed vertices in our map
        m_vertices[frameSample].resize(points.size());
        m_vertices[frameSample] = points;
    }

    // Read OpenSubdiv structures
    {
        VtIntArray creaseIndicesArray;
        if (mesh.GetCreaseIndicesAttr().Get(&creaseIndicesArray))
        {
            m_creaseIndices = std::vector<int>(creaseIndicesArray.begin(), creaseIndicesArray.end());
        }

        VtIntArray creaseLengthsArray;
        if (mesh.GetCreaseLengthsAttr().Get(&creaseLengthsArray))
        {
            m_creaseLengths = std::vector<int>(creaseLengthsArray.begin(), creaseLengthsArray.end());
        }

        VtFloatArray creaseSharpnessArray;
        if (mesh.GetCreaseSharpnessesAttr().Get(&creaseSharpnessArray))
        {
            m_creaseSharpness = std::vector<float>(creaseSharpnessArray.begin(), creaseSharpnessArray.end());
        }

        VtIntArray cornerIndicesArray;
        if (mesh.GetCornerIndicesAttr().Get(&cornerIndicesArray))
        {
            m_cornerIndices = std::vector<int>(cornerIndicesArray.begin(), cornerIndicesArray.end());
        }

        VtFloatArray cornerSharpnessArray;
        if (mesh.GetCornerSharpnessesAttr().Get(&cornerSharpnessArray))
        {
            m_cornerSharpness = std::vector<float>(cornerSharpnessArray.begin(), cornerSharpnessArray.end());
        }

        VtIntArray holeIndicesArray;
        if (mesh.GetHoleIndicesAttr().Get(&holeIndicesArray))
        {
            m_holeIndices = std::vector<int>(holeIndicesArray.begin(), holeIndicesArray.end());
        }

        m_isSubdivMesh = false;
        TfToken subdivisionScheme;
        if (mesh.GetSubdivisionSchemeAttr().Get(&subdivisionScheme))
        {
            if (subdivisionScheme == UsdGeomTokens->none)
            {
                // This mesh is not subdivideable
                m_isSubdivMesh = false;
            }
            else
            {
                m_isSubdivMesh = true;

                if (subdivisionScheme == UsdGeomTokens->catmullClark)
                {
                    m_subdivisionScheme = "catmullClark";
                }
                else if (subdivisionScheme == UsdGeomTokens->loop)
                {
                    m_subdivisionScheme = "loop";
                }
                else if (subdivisionScheme == UsdGeomTokens->bilinear)
                {
                    m_subdivisionScheme = "bilinear";
                }

                TfToken interpolateBoundary;
                if (mesh.GetInterpolateBoundaryAttr().Get(&interpolateBoundary, UsdTimeCode::EarliestTime()))
                {
                    if (interpolateBoundary == UsdGeomTokens->none)
                    {
                        m_interpolateBoundary = 0;
                    }
                    else if (interpolateBoundary == UsdGeomTokens->edgeAndCorner)
                    {
                        m_interpolateBoundary = 1;
                    }
                    else if (interpolateBoundary == UsdGeomTokens->edgeOnly)
                    {
                        m_interpolateBoundary = 2;
                    }
                }

                TfToken faceVaryingLinearInterpolation;
                if (mesh.GetFaceVaryingLinearInterpolationAttr().Get(&faceVaryingLinearInterpolation, UsdTimeCode::EarliestTime()))
                {
                    // See MriOpenSubdivDialog::faceVaryingBoundaryInterpolationFromInt for reference

                    if (faceVaryingLinearInterpolation == UsdGeomTokens->all)
                    {
                        m_faceVaryingLinearInterpolation = 0;
                    }
                    else if (faceVaryingLinearInterpolation == UsdGeomTokens->cornersPlus1)
                    {
                        m_faceVaryingLinearInterpolation = 1;
                        m_propagateCorner = 0;
                    }
                    else if (faceVaryingLinearInterpolation == UsdGeomTokens->none)
                    {
                        m_faceVaryingLinearInterpolation = 2;
                    }
                    else if (faceVaryingLinearInterpolation == UsdGeomTokens->boundaries)
                    {
                        m_faceVaryingLinearInterpolation = 3;
                    }
                    else if (faceVaryingLinearInterpolation == UsdGeomTokens->cornersPlus2)
                    {
                        m_faceVaryingLinearInterpolation = 1;
                        m_propagateCorner = 1;
                    }
                    else if (faceVaryingLinearInterpolation == UsdGeomTokens->cornersOnly)
                    {
                        m_faceVaryingLinearInterpolation = 5;
                    }
                }
                
                TfToken triangleSubdivision;
                if (mesh.GetTriangleSubdivisionRuleAttr().Get(&triangleSubdivision, UsdTimeCode::EarliestTime()))
                {
                    if (triangleSubdivision == UsdGeomTokens->catmullClark)
                    {
                        m_triangleSubdivision = 0;
                    }
                    else if (triangleSubdivision == UsdGeomTokens->smooth)
                    {
                        m_triangleSubdivision = 1;
                    }
                }
            }
        }
    }
}

GeoData::~GeoData()
{
    Reset();
}


// Print the internal status of the Geometric Data.
void GeoData::Log(const PluginHosts* /*pluginHosts*/)
{
}

// Cast to bool. False if no good data is found.
GeoData::operator bool()
{
    return (m_vertices.size() > 0 && m_vertices.begin()->second.size()>0 && m_vertexIndices.size()>0);
}

// Static - Sanity test to see if the usd prim is something we can use.
bool GeoData::IsValidNode(UsdPrim const &prim)
{
    if (not prim.IsA<UsdGeomMesh>())
        return false;
    else
        return TestPath( prim.GetPath().GetText());
}

void GeoData::SetRightHandedWindingOrder(bool rightHandedWindingOrder)
{
    m_isRightHandWindingOrder = rightHandedWindingOrder;
}

//------------------------------------------------------------------------------
/// Helper function to check if an asset path references an Alembic file
static bool IsAlembicAssetPath(const std::string& AssetPath)
{
    if (AssetPath.length() < 4)
    {
        return false;
    }

    std::string Extension = AssetPath.substr(AssetPath.length() - 4);
    // Case-insensitive comparison for .abc extension
    std::transform(Extension.begin(), Extension.end(), Extension.begin(), ::tolower);
    return Extension == ".abc";
}

//------------------------------------------------------------------------------
/// Helper function to detect if a prim or its ancestors reference an Alembic file
static bool HasAlembicPayload(UsdPrim const &Prim)
{
    // Check the prim and walk up the hierarchy to find any Alembic payloads/references
    UsdPrim CurrentPrim = Prim;

    while (CurrentPrim)
    {
        // Check for payloads using composition query
        if (CurrentPrim.HasPayload())
        {
            // Try all list op types
            SdfPayloadListOp PayloadListOp;
            if (CurrentPrim.GetMetadata(SdfFieldKeys->Payload, &PayloadListOp))
            {
                std::vector<SdfPayloadVector> AllPayloads = {
                    PayloadListOp.GetExplicitItems(),
                    PayloadListOp.GetAddedItems(),
                    PayloadListOp.GetPrependedItems(),
                    PayloadListOp.GetAppendedItems()
                };

                for (const auto& PayloadList : AllPayloads)
                {
                    for (const auto& Payload : PayloadList)
                    {
                        if (IsAlembicAssetPath(Payload.GetAssetPath()))
                        {
                            return true;
                        }
                    }
                }
            }
        }

        // Check for references
        if (CurrentPrim.HasAuthoredReferences())
        {
            SdfReferenceListOp ReferenceListOp;
            if (CurrentPrim.GetMetadata(SdfFieldKeys->References, &ReferenceListOp))
            {
                std::vector<SdfReferenceVector> AllReferences = {
                    ReferenceListOp.GetExplicitItems(),
                    ReferenceListOp.GetAddedItems(),
                    ReferenceListOp.GetPrependedItems(),
                    ReferenceListOp.GetAppendedItems()
                };

                for (const auto& ReferenceList : AllReferences)
                {
                    for (const auto& Reference : ReferenceList)
                    {
                        if (IsAlembicAssetPath(Reference.GetAssetPath()))
                        {
                            return true;
                        }
                    }
                }
            }
        }

        // Move up to parent
        CurrentPrim = CurrentPrim.GetParent();
    }

    return false;
}

//------------------------------------------------------------------------------
// Pre-scan the UsdStage to see what uv sets are included.
void GeoData::GetUvSets(UsdPrim const &Prim, UVSet &retval)
{
    UsdGeomGprim   gprim(Prim);
    if (not gprim)
        return;

    // Check if this prim or any ancestor references an Alembic file
    bool IsAlembicPayload = HasAlembicPayload(Prim);

    UsdGeomPrimvarsAPI gPrimApi(gprim);

    std::vector<UsdGeomPrimvar> primvars = gPrimApi.GetPrimvars();
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
            std::string prefix = name.GetString().substr(0,2);
            std::string mapName("");
        
            if ((prefix == "v_" || prefix == "u_") and
                (typeName == SdfValueTypeNames->FloatArray))
            {
                mapName = name.GetString().substr(2);
            } else if (typeName == SdfValueTypeNames->TexCoord2fArray ||
               (GeoData::ReadFloat2AsUV() &&
                typeName == SdfValueTypeNames->Float2Array))
            {
                mapName = name.GetString();
            }
            if (mapName.length()) {
                // For Alembic payloads, only include the "st" UV set to avoid redundancy.
                // The usdAbc plugin creates both "st" (USD standard) and the original
                // Alembic UV set names, which reference the same data.
                if (IsAlembicPayload && mapName != "st")
                {
                    continue;
                }

                UVSet::iterator it = retval.find(mapName);
                if (it == retval.end())
                    retval[mapName] = 1;
                else
                    retval[mapName] += 1;
            }
        }
    }
}

float* GeoData::GetVertices(int frameSample)
{
    if (m_vertices.size() > 0)
    {
        if (m_vertices.find(frameSample) != m_vertices.end())
        {
            return &(m_vertices[frameSample][0]);
        }
        else
        {
            // Could not find frame -> let's return frame 0
            return &(m_vertices.begin()->second[0]);
        }
    }

    // frame not found.
    return NULL;
}

void GeoData::Reset()
{
    m_vertexIndices.clear();
    m_faceCounts.clear();
    m_faceSelectionIndices.clear();

    m_vertices.clear();

    m_normalIndices.clear();
    m_normals.clear();

    m_uvIndices.clear();
    m_uvs.clear();

    m_creaseIndices.clear();
    m_creaseLengths.clear();
    m_creaseSharpness.clear();
    m_cornerIndices.clear();
    m_cornerSharpness.clear();
    m_holeIndices.clear();
}

bool GeoData::TestPath(std::string path)
{
    bool requiredSubstringFound = true;
    std::vector<std::string>::iterator i;
    for (i=_requireGeomPathSubstring.begin(); i!=_requireGeomPathSubstring.end(); ++i)
    {
        if (path.find(*i) != std::string::npos)
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
        if (path.find(*i) != std::string::npos)
        {
            return false;
        }
    }
    return true;
}
    

void GeoData::InitializePathSubstringLists()
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
bool GeoData::CastVtValueAs(SOURCE &obj, TYPE &result)
{
    if ( obj.template CanCast<TYPE>() ) 
    {
        obj = obj.template Cast<TYPE>();
        result = obj.template Get<TYPE>();
        return true;
    }
    return false;
}

