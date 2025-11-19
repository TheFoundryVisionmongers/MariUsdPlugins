//
// Copyright(c) 2025 The Foundry Visionmongers Ltd.All Rights Reserved.
//

#pragma once

#include <pxr/base/gf/matrix4f.h>
#include <pxr/usd/usdGeom/camera.h>

#include "MariHostConfig.h"

/// Represents a camera in a USD scene.
class CameraData
{
public:
    /// Constructor.
    /// \param prim The USD prim.
    explicit CameraData(PXR_NS::UsdPrim const& prim);

    /// Valid nodes are cameras.
    /// \param prim The USD prim.
    /// \return true if the prim is a camera; false otherwise.
    static bool IsValidNode(PXR_NS::UsdPrim const& prim);

    /// Make a Mari entity from this camera prim.
    /// \param pluginHosts The plugin hosts.
    /// \param parentEntity The parent entity.
    /// \return true on success; false otherwise.
    bool MakeEntity(const PluginHosts* pluginHosts, MriUserItemHandle parentEntity) const;

private:
    PXR_NS::UsdPrim                 m_prim;
    PXR_NS::TfToken                 m_projection;
    std::string                     m_name;
    std::vector<PXR_NS::GfMatrix4f> m_xformOps;                 // Ordered list of transform operations from USD
    std::list<std::string>          m_xformOpOrder;             // List of xformOp names for round-tripping
    PXR_NS::GfMatrix4f              m_xform;                    // Flattened world transform for extracting vectors
    PXR_NS::GfVec3f                 m_forward;
    PXR_NS::GfVec3f                 m_up;
    float                           m_horizontalAperture{};
    float                           m_verticalAperture{};
    float                           m_focalLength{};
    float                           m_fovX{};
    float                           m_fovY{};
    PXR_NS::GfVec2f                 m_clippingRange;
};
