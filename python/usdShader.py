import mari
import os

if mari.app.isRunning():
    usd_path = mari.resources.bundledUsdPath()

    shader_path = os.path.join(usd_path, "shaders")
    mari.gl_render.registerCustomHeaderFile("mriUsdPreviewSurfaceFuncsHeader", os.path.join(shader_path, "mriUsdPreviewSurfaceFuncs.glslh"))
    mari.gl_render.registerCustomCodeFile("mriUsdPreviewSurfaceFuncsBody", os.path.join(shader_path, "mriUsdPreviewSurfaceFuncs.glslc"))
    
    node_path = os.path.join(usd_path, "nodes")
    mari.gl_render.registerCustomStandaloneShaderFromXMLFile("USD Preview Surface", os.path.join(node_path, "mriUsdPreviewSurface.xml"))