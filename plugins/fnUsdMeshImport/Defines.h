//
// Copyright(c) 2025 The Foundry Visionmongers Ltd.All Rights Reserved.
//

#pragma once

#ifdef _WIN32
    #define USD_PLUGIN_EXPORT_SYMBOL __declspec(dllexport)
#else
    #define USD_PLUGIN_EXPORT_SYMBOL __attribute__((visibility("default")))
#endif
