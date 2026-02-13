//
// Copyright(c) 2026 The Foundry Visionmongers Ltd. All Rights Reserved.
//

#include "CameraAdapter.h"
#include "CameraData.h"

#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usd/primRange.h>
#include <pxr/usd/usdGeom/camera.h>
#include <pxr/base/tf/stringUtils.h>

PXR_NAMESPACE_USING_DIRECTIVE

namespace
{
    UsdStageRefPtr openUsdStage(const char* fileName, std::string& errorMsg)
    {
        UsdStageRefPtr stage = UsdStage::Open(fileName);
        if (!stage)
        {
            errorMsg = "Failed to open USD file: ";
            errorMsg += fileName;
        }
        return stage;
    }
}

MriCameraPluginResult CameraAdapter::LoadFromFile(
    MriCameraHandle cameraHandle,
    const char* fileName,
    const MriCameraReaderHostV1* cameraHost,
    std::string& messagesOut)
{
    if (!fileName || !cameraHost)
    {
        messagesOut = "Invalid parameters";
        return MRI_CAM_INVALID_POINTER;
    }

    // Open USD stage
    UsdStageRefPtr stage = openUsdStage(fileName, messagesOut);
    if (!stage)
    {
        return MRI_CAM_FILE_OPEN_FAILED;
    }

    // Find first camera in stage
    UsdPrim cameraPrim;
    for (const UsdPrim& prim : stage->Traverse())
    {
        if (CameraData::IsValidNode(prim))
        {
            cameraPrim = prim;
            break;
        }
    }

    if (!cameraPrim)
    {
        messagesOut = "No camera found in USD file";
        return MRI_CAM_FAILED;
    }

    // Read camera data from USD
    CameraData cameraData(cameraPrim);

    // Adapt to Camera Reader API
    if (!AdaptCameraData(cameraData, cameraHandle, cameraHost))
    {
        messagesOut = "Failed to create camera from USD data";
        return MRI_CAM_FAILED;
    }

    messagesOut = "Successfully loaded camera: ";
    messagesOut += cameraPrim.GetName().GetString();
    return MRI_CAM_SUCCEEDED;
}

MriCameraPluginResult CameraAdapter::GetFrameRange(
    const char* fileName,
    int* startFrame,
    int* endFrame,
    std::string& messagesOut)
{
    if (!fileName || !startFrame || !endFrame)
    {
        return MRI_CAM_INVALID_POINTER;
    }

    // Open USD stage
    UsdStageRefPtr stage = openUsdStage(fileName, messagesOut);
    if (!stage)
    {
        return MRI_CAM_FILE_OPEN_FAILED;
    }

    // Get time code range from stage
    double startTimeCode = stage->GetStartTimeCode();
    double endTimeCode = stage->GetEndTimeCode();

    *startFrame = static_cast<int>(startTimeCode);
    *endFrame = static_cast<int>(endTimeCode);

    return MRI_CAM_SUCCEEDED;
}

bool CameraAdapter::AdaptCameraData(
    const CameraData& cameraData,
    MriCameraHandle cameraHandle,
    const MriCameraReaderHostV1* cameraHost)
{
    // Determine camera type from USD projection attribute
    TfToken projection = cameraData.GetProjection();
    MriCameraType cameraType = (projection == UsdGeomTokens->orthographic) 
        ? MRI_CAM_ORTHO 
        : MRI_CAM_PERSPECTIVE;

    // Create camera with name
    std::string cameraName = cameraData.GetName();
    if (cameraHost->createCamera(cameraHandle, cameraType, cameraName.c_str()) != MRI_CAM_SUCCEEDED)
    {
        return false;
    }

    // Set camera properties for frame 0 (or could iterate through animation frames)
    const int frame = 0;

    // Extract position from transform matrix
    GfVec3f position = cameraData.GetPosition();
    if (cameraHost->setTranslation(cameraHandle, frame, position[0], position[1], position[2]) != MRI_CAM_SUCCEEDED)
    {
        return false;
    }

    // Set look at vector (forward direction)
    GfVec3f forward = cameraData.GetForward();
    GfVec3f lookAt = position + forward; // Camera position + forward vector
    if (cameraHost->setLookAt(cameraHandle, frame, lookAt[0], lookAt[1], lookAt[2]) != MRI_CAM_SUCCEEDED)
    {
        return false;
    }

    // Set up vector
    GfVec3f up = cameraData.GetUp();
    if (cameraHost->setUp(cameraHandle, frame, up[0], up[1], up[2]) != MRI_CAM_SUCCEEDED)
    {
        return false;
    }

    // Set field of view
    float fovX = cameraData.GetFovX();
    float fovY = cameraData.GetFovY();
    if (cameraHost->setFov(cameraHandle, frame, fovX, fovY) != MRI_CAM_SUCCEEDED)
    {
        return false;
    }

    // Set clipping planes
    GfVec2f clippingRange = cameraData.GetClippingRange();
    if (cameraHost->setNear(cameraHandle, frame, clippingRange[0]) != MRI_CAM_SUCCEEDED)
    {
        return false;
    }
    if (cameraHost->setFar(cameraHandle, frame, clippingRange[1]) != MRI_CAM_SUCCEEDED)
    {
        return false;
    }

    // Set custom attributes (focal length, aperture, etc.) for round-tripping
    MriAttributeValue attrValue;

    attrValue.m_Type = MRI_ATTR_DOUBLE;
    attrValue.m_Double = cameraData.GetFocalLength();
    cameraHost->setAttribute(cameraHandle, "USD_focalLength", &attrValue);

    attrValue.m_Double = cameraData.GetHorizontalAperture();
    cameraHost->setAttribute(cameraHandle, "USD_horizontalAperture", &attrValue);

    attrValue.m_Double = cameraData.GetVerticalAperture();
    cameraHost->setAttribute(cameraHandle, "USD_verticalAperture", &attrValue);

    return true;
}
