//
// Copyright(c) 2025 The Foundry Visionmongers Ltd.All Rights Reserved.
//

#include "Diagnostics.h"

namespace
{
    auto formatDiagnostic(PXR_NS::TfDiagnosticBase const& d)
    {
        std::string const msg = PXR_NS::TfStringPrintf("%s -- %s in %s at line %zu of %s",
            d.GetCommentary().c_str(),
            PXR_NS::TfDiagnosticMgr::GetCodeName(d.GetDiagnosticCode()).c_str(),
            d.GetContext().GetFunction(),
            d.GetContext().GetLine(),
            d.GetContext().GetFile());
        return msg;
    }
}

DiagnosticDelegate::DiagnosticDelegate(const PluginHosts* pluginHosts) : m_pluginHosts(pluginHosts)
{
}

void DiagnosticDelegate::IssueError(const PXR_NS::TfError& err)
{
    const auto message = formatDiagnostic(err);
    m_pluginHosts->geoReaderHost.trace("%s\n", message.data());
}

void DiagnosticDelegate::IssueFatalError(const PXR_NS::TfCallContext& /*context*/, const std::string& message)
{
    m_pluginHosts->geoReaderHost.trace("%s\n", message.data());
}

void DiagnosticDelegate::IssueWarning(const PXR_NS::TfWarning& warning)
{
    const auto message = formatDiagnostic(warning);
    m_pluginHosts->geoReaderHost.trace("%s\n", message.data());
}

void DiagnosticDelegate::IssueStatus(const PXR_NS::TfStatus& status)
{
    const auto message = formatDiagnostic(status);
    m_pluginHosts->geoReaderHost.trace("%s\n", message.data());
}
