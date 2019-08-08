#ifndef GEO_DATA_H
#define GEO_DATA_H

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
        
        // get
        float* GetVertices(int frame = -1);
        float* GetNormals(int frame = -1);

        // return recommended selection set name, number of faces
        // and face indices for this geom.
        void GetSelectionGroup(std::string& name, 
            int &size, int*& faceIndices);

        typedef unsigned* uptr;

        inline uptr GetIndices() {return (unsigned*)&(_indices[0]);}
        inline uptr GetFaceIndices() {return (unsigned*)&(_faceIndices[0]);}
        inline uptr GetFaceVertexCounts() {return (unsigned*)&(_vertsPerFace[0]);}
        inline uptr GetCreaseIndices() {return (unsigned*)&(_creaseIndices[0]);}
        inline uptr GetCreaseLengths() {return (unsigned*)&(_creaseLengths[0]);}
        inline float* GetCreaseSharpness() {return &(_creaseSharpness[0]);}
        inline float* GetUVs() {return &(_uvs[0]);}
        inline uptr GetUVIndices() {return (unsigned*)&(_uvIndices[0]);}
        inline bool HasUVs() {return (_uvs.size() != 0);}
        inline int GetNumTriangles() {return _numTriangles;}
        inline int GetNumPoints() {return _vertices.begin()->second.size();}
        inline int GetNumIndices() {return _indices.size();}
        inline int GetNumFaceVertices() {return _numFaceVertices;}
        inline int GetNumFaceVertexCounts() {return _numFaceVertCounts;}
        inline int GetNumCreaseIndices() {return _creaseIndices.size();}
        inline int GetNumCreaseLengths() {return _creaseLengths.size();}
        inline int GetNumCreaseSharpness() {return _creaseSharpness.size();}

        // is valid?
        operator bool();

private:
        void _NudgeUVs(std::vector<float>& u, 
                       std::vector<float>& v, 
                       const std::vector<int>& vertsIndices,
                       const std::vector<int>& numVertsPerFace,
                       const MriGeoReaderHost& host);
        void _BuildMariGeoData(const int frame,
                               const int iFrame,
                               const int nFaces,
                               const bool leftHandedness,
                               const std::vector<int>& nvertsPerFace,
                               const std::vector<float>& points,
                               const std::vector<int>& vertIndices,
                               const std::string& uvSet,
                               const bool faceVaryingUU,
                               const bool faceVaryingVV,
                               const std::vector<float>& uu,
                               const std::vector<float>& vv,
                               const MriGeoReaderHost& host);
        void _CalculateFaceIndices();

        
protected:
        int _numTriangles;
        int _numFaceVertices;
        int _numFaceVertCounts;
        
        std::vector<float> _uvs;
        std::vector<int> _uvIndices;
        std::vector<float> _creaseSharpness;
        std::map<int, std::vector<float> > _vertices;
        std::map<int, std::vector<float> > _normals;
        std::vector<unsigned int> _indices;
        std::vector<int> _faceIndices;   // used for selection sets
        std::vector<int> _normalIndices;
        std::vector<int> _creaseIndices;
        std::vector<int> _creaseLengths;
        std::vector<int> _vertsPerFace;
        std::string _selectionGroupName;
        static std::string _requireGeomPathSubstringEnvVar;
        static std::string _ignoreGeomPathSubstringEnvVar;
        static std::vector<std::string> _requireGeomPathSubstring;
        static std::vector<std::string> _ignoreGeomPathSubstring;
};

#endif //GEO_DATA_H
