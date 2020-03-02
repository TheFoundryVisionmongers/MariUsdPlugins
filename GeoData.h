#ifndef GEO_DATA_H
#define GEO_DATA_H

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

#include <set>
#include <vector>
#include "MriGeoReaderPlugin.h"

#include "pxr/usd/usd/prim.h"

#include "MariHostConfig.h"


class GeoData
{
    /*
    This class helps describe a valid gprim for mari purposes.
    Many of these can be pertinent to a single ModelData.
    */    
public:

        typedef std::map<std::string, int> UVSet;

        static void GetUvSets(PXR_NS::UsdPrim const &prim, UVSet &retval);

        // Valid nodes are meshes, and subdivs, included in a "Geom" group
        static bool IsValidNode(PXR_NS::UsdPrim const &prim);

        // Check the geometry path against a "required" and "ignore" 
        // list of substrings.
        static bool TestPath(std::string path);

        template <typename SOURCE, typename TYPE>
        static bool CastVtValueAs(SOURCE &obj, TYPE &result);

        static void InitializePathSubstringLists();

        static bool ReadFloat2AsUV();

        // create geoData
        GeoData(PXR_NS::UsdPrim const &prim,
                std::string uvSet, // requested uvSet 
                std::vector<int> frames,
                bool keepCentered,
                PXR_NS::UsdPrim const &model,
                const MriGeoReaderHost& host,
                std::vector<std::string>& log);
        
        ~GeoData();
     
        // print content
        void Log(const MriGeoReaderHost& host);
                
        // reset
        void Reset();

        typedef unsigned* uptr;

        inline uptr GetVertexIndices() {return (unsigned*)&(m_vertexIndices[0]);}
        inline int GetNumVertexIndices() {return m_vertexIndices.size();}

        inline uptr GetFaceVertexCounts() {return (unsigned*)&(m_faceCounts[0]);}
        inline int GetNumFaceVertexCounts() {return m_faceCounts.size();}

        inline int* GetFaceSelectionIndices() {return &(m_faceSelectionIndices[0]);}

        float* GetVertices(int frameSample);
        inline int GetNumPoints() {return m_vertices.begin()->second.size();}

        inline bool HasNormals() {return (m_normals.size() != 0);}
        inline uptr GetNormalIndices() {return (unsigned*)&(m_normalIndices[0]);}
        inline float* GetNormals() {return &(m_normals[0]);}
        inline int GetNumNormals() {return m_normals.size();}

        inline bool HasUVs() {return (m_uvs.size() != 0);}
        inline uptr GetUVIndices() {return (unsigned*)&(m_uvIndices[0]);}
        inline float* GetUVs() {return &(m_uvs[0]);}
        inline int GetNumUvs() {return m_uvs.size();}

        inline uptr GetCreaseIndices() {return (unsigned*)&(m_creaseIndices[0]);}
        inline int GetNumCreaseIndices() {return m_creaseIndices.size();}

        inline uptr GetCreaseLengths() {return (unsigned*)&(m_creaseLengths[0]);}
        inline int GetNumCreaseLengths() {return m_creaseLengths.size();}

        inline float* GetCreaseSharpness() {return &(m_creaseSharpness[0]);}
        inline int GetNumCreaseSharpness() {return m_creaseSharpness.size();}

        inline uptr GetCornerIndices() {return (unsigned*)&(m_cornerIndices[0]);}
        inline int GetNumCornerIndices() {return m_cornerIndices.size();}

        inline float* GetCornerSharpness() {return &(m_cornerSharpness[0]);}
        inline int GetNumCornerSharpness() {return m_cornerSharpness.size();}

        inline uptr GetHoleIndicess() {return (unsigned*)&(m_holeIndices[0]);}
        inline int GetNumHoleIndices() {return m_holeIndices.size();}

        inline bool IsSubdivMesh() {return m_isSubdivMesh;}
        inline std::string SubdivisionScheme() {return m_subdivisionScheme;}
        inline int InterpolateBoundary() {return m_interpolateBoundary;}
        inline int FaceVaryingLinearInterpolation() {return m_faceVaryingLinearInterpolation;}
        inline int PropagateCorner() {return m_propagateCorner;}

        // is valid?
        operator bool();

protected:
        std::vector<int> m_vertexIndices;
        std::vector<int> m_faceCounts;
        std::vector<int> m_faceSelectionIndices;

        std::map<int, std::vector<float> > m_vertices;

        std::vector<int> m_normalIndices;
        std::vector<float> m_normals;

        std::vector<int> m_uvIndices;
        std::vector<float> m_uvs;

        std::vector<int> m_creaseIndices;
        std::vector<int> m_creaseLengths;
        std::vector<float> m_creaseSharpness;
        std::vector<int> m_cornerIndices;
        std::vector<float> m_cornerSharpness;
        std::vector<int> m_holeIndices;

        bool m_isSubdivMesh;
        std::string m_subdivisionScheme;
        int m_interpolateBoundary;
        int m_faceVaryingLinearInterpolation;
        int m_propagateCorner;

        static std::string _requireGeomPathSubstringEnvVar;
        static std::string _ignoreGeomPathSubstringEnvVar;
        static std::vector<std::string> _requireGeomPathSubstring;
        static std::vector<std::string> _ignoreGeomPathSubstring;
};

#endif //GEO_DATA_H
