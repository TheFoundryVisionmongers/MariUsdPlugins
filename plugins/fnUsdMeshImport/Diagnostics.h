//
// Copyright(c) 2025 The Foundry Visionmongers Ltd.All Rights Reserved.
//

#pragma once

#include <MriCameraReaderPlugin.h>
#include <MriGeoReaderPlugin.h>
#include <pxr/base/tf/diagnosticMgr.h>

#include "MariHostConfig.h"

/// Delegate for USD's diagnostic system, enabling USD's diagnostic messages
/// to be shown in Mari's logging system.
class DiagnosticDelegate final : public PXR_NS::TfDiagnosticMgr::Delegate
{
public:
    /// Constructor.
    DiagnosticDelegate(const PluginHosts* pluginHosts);

    /// Called when a \c TfError is posted.
    void IssueError(const PXR_NS::TfError& err) final;

    /// Called when a \c TF_FATAL_ERROR is issued (or a failed \c TF_AXIOM).
    void IssueFatalError(const PXR_NS::TfCallContext& context, const std::string& msg) final;

    /// Called when a \c TF_STATUS() is issued.
    void IssueStatus(const PXR_NS::TfStatus& status) final;

    /// Called when a \c TF_WARNING() is issued.
    void IssueWarning(const PXR_NS::TfWarning& warning) final;

private:
    const PluginHosts* m_pluginHosts;
};
