//
// Copyright(c) 2025 The Foundry Visionmongers Ltd.All Rights Reserved.
//

#include "CameraData.h"

#include <pxr/usd/usdGeom/xformCache.h>
#include <pxr/usd/usdGeom/xformable.h>

PXR_NAMESPACE_USING_DIRECTIVE

namespace
{
    bool addFloatAttribute(MriSceneBuilderCamera* pCamera, const char* name, const float value)
    {
        MriAttributeValue attrValue;
        attrValue.m_Type = MRI_ATTR_DOUBLE;
        attrValue.m_Double = value;

        return pCamera->setAttribute(pCamera->handle, name, &attrValue) == MRI_UPR_SUCCEEDED;
    }

    bool addStringListAttribute(MriSceneBuilderCamera* pCamera, const char* name, const std::list<std::string>& value)
    {
        auto joinWithNewline = [](const std::string& a, const std::string& b) { return a + "\n" + b; };
        std::string stringValue = std::accumulate(std::next(value.begin()), value.end(), value.empty() ? "" : value.front(), joinWithNewline);

        MriAttributeValue attrValue;
        attrValue.m_Type = MRI_ATTR_STRING_LIST;
        attrValue.m_pString = stringValue.data();

        return pCamera->setAttribute(pCamera->handle, name, &attrValue) == MRI_UPR_SUCCEEDED;
    }
}

CameraData::CameraData(PXR_NS::UsdPrim const& prim) : m_prim(prim)
{
    // Get camera schema to read properties
    UsdGeomCamera camera(prim);

    // Get the name.
    m_name = prim.GetName().GetString();

    // Get the projection type.
    camera.GetProjectionAttr().Get(&m_projection);

    // Get camera transform operations from USD for round-tripping
    // Store each xformOp as a matrix so we can recreate the stack later
    UsdGeomXformable xformable(prim);
    bool resetXformStack = false;
    std::vector<UsdGeomXformOp> xformOps = xformable.GetOrderedXformOps(&resetXformStack);
    
    // Store each xform operation as a matrix and build xformOpOrder string
    for (size_t i = 0; i < xformOps.size(); ++i)
    {
        const auto& xformOp = xformOps[i];

        // Get the matrix for this specific operation
        m_xformOps.push_back(GfMatrix4f(xformOp.GetOpTransform(UsdTimeCode::Default().GetValue())));
        m_xformOpOrder.emplace_back(xformOp.GetOpName().GetString());
    }
    
    // Compute the flattened transform for extracting camera vectors
    UsdGeomXformCache xformCache;
    m_xform = GfMatrix4f(xformCache.GetLocalToWorldTransform(prim));

    // Calculate look at and up vectors from transform matrix.
    m_forward = -m_xform.GetRow3(2).GetNormalized(); // -Z is forward in USD.
    m_up = m_xform.GetRow3(1).GetNormalized();       // +Y is up in USD.

    // Get FOV from horizontal and vertical aperture and focal length.
    camera.GetHorizontalApertureAttr().Get(&m_horizontalAperture);
    camera.GetVerticalApertureAttr().Get(&m_verticalAperture);
    camera.GetFocalLengthAttr().Get(&m_focalLength);

    // Convert to FOV in degrees.
    // FOV = 2 * atan(aperture / (2 * focal_length)) * (180 / pi)
    m_fovX = 2.0f * std::atan(m_horizontalAperture / (2.0f * m_focalLength)) * 180.0f / static_cast<float>(M_PI);
    m_fovY = 2.0f * std::atan(m_verticalAperture / (2.0f * m_focalLength)) * 180.0f / static_cast<float>(M_PI);

    // Get near/far clipping planes.
    // USD clipping range is in camera space units, Mari expects millimeters.
    // USD typically uses cm, so convert cm to mm.
    camera.GetClippingRangeAttr().Get(&m_clippingRange);
}

bool CameraData::IsValidNode(UsdPrim const& prim)
{
    return prim.IsA<UsdGeomCamera>();
}

bool CameraData::MakeEntity(const PluginHosts* pluginHosts, MriUserItemHandle parentEntity) const
{
    MriSceneBuilderCamera* pCamera{};
    if (pluginHosts->geoReaderHost.createSceneBuilderCamera(parentEntity, &pCamera) != MRI_GPR_SUCCEEDED)
    {
        return false;
    }

    // Set the name.
    if (pCamera->setEntityName(pCamera, m_name.data()) != MRI_SCENE_BUILDER_SUCCEEDED)
    {
        return false;
    }

    // Set the type.
    const auto cameraType = (m_projection == UsdGeomTokens->orthographic) ? MRI_SCENE_CAM_ORTHOGRAPHIC : MRI_SCENE_CAM_PERSPECTIVE;
    if (pCamera->setCameraType(pCamera, cameraType) != MRI_SCENE_BUILDER_SUCCEEDED)
    {
        return false;
    }

    const int frame = 0;

    // Add each transform operation in order to preserve the USD xform stack
    for (const auto& xformMatrix : m_xformOps)
    {
        const float matrix[16] = {
            xformMatrix[0][0], xformMatrix[0][1], xformMatrix[0][2], xformMatrix[0][3],
            xformMatrix[1][0], xformMatrix[1][1], xformMatrix[1][2], xformMatrix[1][3],
            xformMatrix[2][0], xformMatrix[2][1], xformMatrix[2][2], xformMatrix[2][3],
            xformMatrix[3][0], xformMatrix[3][1], xformMatrix[3][2], xformMatrix[3][3]
        };
        pCamera->addTransform(pCamera, frame, matrix);
    }

    if (pCamera->setLookAt(pCamera, frame, m_forward[0], m_forward[1], m_forward[2]) != MRI_SCENE_BUILDER_SUCCEEDED)
    {
        return false;
    }
    
    if (pCamera->setUp(pCamera, frame, m_up[0], m_up[1], m_up[2]) != MRI_SCENE_BUILDER_SUCCEEDED)
    {
        return false;
    }

    if (pCamera->setFov(pCamera, frame, m_fovX, m_fovY) != MRI_SCENE_BUILDER_SUCCEEDED)
    {
        return false;
    }
    
    if (pCamera->setNear(pCamera, frame, m_clippingRange[0] * 10.0f) != MRI_SCENE_BUILDER_SUCCEEDED)
    {
        return false;
    }
    
    if (pCamera->setFar(pCamera, frame, m_clippingRange[1] * 10.0f) != MRI_SCENE_BUILDER_SUCCEEDED)
    {
        return false;
    }

    if (!addFloatAttribute(pCamera, "USD_focalLength", m_focalLength))
    {
        return false;
    }
    
    if (!addFloatAttribute(pCamera, "USD_horizontalAperture", m_horizontalAperture))
    {
        return false;
    }
    
    if (!addFloatAttribute(pCamera, "USD_verticalAperture", m_verticalAperture))
    {
        return false;
    }

    // Store xformOpOrder for round-tripping back to USD
    if (!m_xformOpOrder.empty())
    {
        addStringListAttribute(pCamera, "USD_xformOpOrder", m_xformOpOrder);
    }

    if (pCamera->setLocked(pCamera, 1) != MRI_SCENE_BUILDER_SUCCEEDED)
    {
        return false;
    }

    return true;
}
