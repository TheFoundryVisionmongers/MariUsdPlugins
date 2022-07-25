import mari
import os
import re
from . import usdShadeExport
from pxr import Sdf, UsdShade

def writeUsdPreviewSurface(looks_stage, usd_shader, usd_export_parameters, usd_shader_source):
    """Function to write out the Usd shading nodes for an input to a UsdPreviewSurface shader.

    Args:
        looks_stage (Usd.Stage): Stage to write to
        usd_shader (Usd.Shader): Shader to connect to
        usd_export_parameters (UsdExportParameters): Container for export parameters
        usd_shader_source (UsdShaderSource): Container of source Shader and Export Item instances
    """
    mari_to_usd_input_map = {
        "diffuseColor": ("diffuseColor", Sdf.ValueTypeNames.Color3f),
        "emissiveColor": ("emissiveColor", Sdf.ValueTypeNames.Color3f),
        "useSpecularWorkflow": ("useSpecularWorkflow", Sdf.ValueTypeNames.Bool),
        "specularColor": ("specularColor", Sdf.ValueTypeNames.Color3f),
        "metallic": ("metallic", Sdf.ValueTypeNames.Float),
        "roughness": ("roughness", Sdf.ValueTypeNames.Float),
        "clearcoat": ("clearcoat", Sdf.ValueTypeNames.Float),
        "clearcoatRoughness": ("clearcoatRoughness", Sdf.ValueTypeNames.Float),
        "opacity": ("opacity", Sdf.ValueTypeNames.Float),
        "opacityThreshold": ("opacityThreshold", Sdf.ValueTypeNames.Float),
        "ior": ("ior", Sdf.ValueTypeNames.Float),
        "Normal": ("normal", Sdf.ValueTypeNames.Normal3f),
        "occlusion": ("occlusion", Sdf.ValueTypeNames.Float),
        "Bump": (None, None),
        "Vector": (None, None),
        "Displacement": ("displacement", Sdf.ValueTypeNames.Float),
    }
    usdShadeExport._debuglog("Writing USD Preview Surface shader network for %s" % usd_shader_source.sourceShader().name())
    material_sdf_path = usd_shader.GetPath().GetParentPath()

    shader_model = usd_shader_source.shaderModel()
    export_items = []
    for shader_input_name in shader_model.inputNames():
        usd_shader_input_name, sdf_type = mari_to_usd_input_map[shader_input_name]
        if usd_shader_input_name is None:
            continue
        export_item = usd_shader_source.getInputExportItem(shader_input_name)
        if export_item is not None:

            # find or define texture coordinate reader
            st_reader_path = material_sdf_path.AppendChild("st_reader")
            st_reader = UsdShade.Shader.Get(looks_stage, st_reader_path)
            if st_reader.GetPath().isEmpty:
                st_reader = UsdShade.Shader.Define(looks_stage, st_reader_path)
                st_reader.CreateIdAttr('UsdPrimvarReader_float2')
                st_reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set(usd_shader_source.uvSetName())

            # TODO: Implement a override option for export that gets passed into this function
            # Perform the texture export
            # if not hasExportItemBeenExported(export_item, export_root_path):
            #     mari.exports.exportTextures([export_item], export_root_path)

            # Create and connect the texture reading shading node
            texture_usd_file_name = re.sub(r"\$UDIM", "<UDIM>", export_item.resolveFileTemplate())
            texture_usd_file_path = os.path.join(usd_export_parameters.exportRootPath(), texture_usd_file_name)
            texture_sampler_sdf_path = material_sdf_path.AppendChild("{0}Texture".format(shader_input_name))
            texture_sampler = UsdShade.Shader.Define(looks_stage, texture_sampler_sdf_path)
            texture_sampler.CreateIdAttr("UsdUVTexture")
            texture_sampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
                st_reader.ConnectableAPI(),
                "result"
            )
            usd_shader.CreateInput(usd_shader_input_name, sdf_type).ConnectToSource(
                texture_sampler.ConnectableAPI(),
                usdShadeExport.colorComponentForType(sdf_type)
            )
            texture_sampler.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_usd_file_path)

            export_items.append(export_item)
        else:
            if shader_input_name not in usd_shader_source.sourceShader().parameterNameList():
                continue
            input_value = usd_shader_source.sourceShader().getParameter(shader_input_name)
            default_color = usd_shader_source.shaderModel().input(shader_input_name).defaultColor()

            if not usdShadeExport.isValueDefault(input_value, default_color):
                usd_shader_parameter = usd_shader.CreateInput(usd_shader_input_name, sdf_type)
                usd_shader_parameter.Set(usdShadeExport.valueAsShaderParameter(input_value, sdf_type))

    # Export textures from export items
    if export_items:
        usdShadeExport._debuglog(
            "Exporting %d export items for %s to %s" % (
                len(export_items),
                usd_shader_source.sourceShader().name(),
                usd_export_parameters.exportRootPath()
            )
        )
        mari.exports.exportTextures(export_items, usd_export_parameters.exportRootPath(), usd_export_parameters.exportOverrides())

if mari.app.isRunning():
    usdShadeExport.registerRendererExportPlugin(
        "USD Preview Surface",
        "UsdPreviewSurface",
        writeUsdPreviewSurface,
        "surface",
        None
    )