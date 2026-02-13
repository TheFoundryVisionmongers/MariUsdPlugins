//
// Copyright(c) 2026 The Foundry Visionmongers Ltd. All Rights Reserved.
//

#pragma once

#include "MriCameraReaderPlugin.h"
#include <string>

class CameraData;

/// Adapter to bridge between USD CameraData and Mari Camera Reader API
class CameraAdapter
{
public:
    /// Load camera from USD file using Camera Reader API
    /// \param cameraHandle Handle provided by Camera Reader host
    /// \param fileName Path to USD file
    /// \param cameraHost Camera Reader host functions
    /// \param messagesOut Output messages (warnings/errors)
    /// \return Success/failure code
    static MriCameraPluginResult LoadFromFile(
        MriCameraHandle cameraHandle,
        const char* fileName,
        const MriCameraReaderHostV1* cameraHost,
        std::string& messagesOut);

    /// Get frame range from USD file
    /// \param fileName Path to USD file
    /// \param startFrame Output: first frame
    /// \param endFrame Output: last frame
    /// \param messagesOut Output messages
    /// \return Success/failure code
    static MriCameraPluginResult GetFrameRange(
        const char* fileName,
        int* startFrame,
        int* endFrame,
        std::string& messagesOut);

private:
    /// Adapt CameraData to Camera Reader API calls
    /// \param cameraData USD camera data
    /// \param cameraHandle Handle for camera being created
    /// \param cameraHost Host functions to call
    /// \return true on success
    static bool AdaptCameraData(
        const CameraData& cameraData,
        MriCameraHandle cameraHandle,
        const MriCameraReaderHostV1* cameraHost);
};
