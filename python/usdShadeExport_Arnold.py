import mari
import os
import re
from . import usdShadeExport
from pxr import Sdf, UsdShade

def writeArnoldStandardSurface(looks_stage, usd_shader, usd_export_parameters, usd_shader_source):
    """Function to write out the Usd shading nodes for an input to an ArnoldStandardSurface shader.

    Args:
        looks_stage (Usd.Stage): Stage to write to
        usd_shader (Usd.Shader): Shader to connect to
        usd_export_parameters (UsdExportParameters): Container for export parameters
        usd_shader_source (UsdShaderSource): Container of source Shader and Export Item instances
    """
    mari_to_usd_input_map = {
#        ('aov_id1', str),
#        ('aov_id2', str),
#        ('aov_id3', str),
#        ('aov_id4', str),
#        ('aov_id5', str),
#        ('aov_id6', str),
#        ('aov_id7', str),
#        ('aov_id8', str),
        "DiffuseWeight":('base', Sdf.ValueTypeNames.Float),
        "DiffuseColor":('base_color', Sdf.ValueTypeNames.Color3f),
#        ('caustics', bool),
        "CoatWeight":('coat', Sdf.ValueTypeNames.Float),
#        ('coat_affect_color', Sdf.ValueTypeNames.Float),
#        ('coat_affect_roughness', Sdf.ValueTypeNames.Float),
#        ('coat_anisotropy', Sdf.ValueTypeNames.Float),
        "CoatColor":('coat_color', Sdf.ValueTypeNames.Color3f),
        "CoatIOR":('coat_IOR', Sdf.ValueTypeNames.Float),
#        ('coat_normal', Sdf.ValueTypeNames.Color3f),
#        ('coat_rotation', Sdf.ValueTypeNames.Float),
        "CoatRoughness":('coat_roughness', Sdf.ValueTypeNames.Float),
#        ('dielectric_priority', int),
        "DiffuseRoughness":('diffuse_roughness', Sdf.ValueTypeNames.Float),
        "EmissionWeight":('emission', Sdf.ValueTypeNames.Float),
        "EmissionColor":('emission_color', Sdf.ValueTypeNames.Color3f),
#        ('exit_to_background', bool),
#        ('id1', Sdf.ValueTypeNames.Color3f),
#        ('id2', Sdf.ValueTypeNames.Color3f),
#        ('id3', Sdf.ValueTypeNames.Color3f),
#        ('id4', Sdf.ValueTypeNames.Color3f),
#        ('id5', Sdf.ValueTypeNames.Color3f),
#        ('id6', Sdf.ValueTypeNames.Color3f),
#        ('id7', Sdf.ValueTypeNames.Color3f),
#        ('id8', Sdf.ValueTypeNames.Color3f),
#        ('indirect_diffuse', Sdf.ValueTypeNames.Float),
#        ('indirect_specular', Sdf.ValueTypeNames.Float),
#        ('internal_reflections', bool),
        "Metalness":('metalness', Sdf.ValueTypeNames.Float),
#        ('name', str),
        "Normal":('normal', Sdf.ValueTypeNames.Normal3f),
        "Opacity":('opacity', Sdf.ValueTypeNames.Color3f),
        "SheenWeight":('sheen', Sdf.ValueTypeNames.Float),
        "SheenColor":('sheen_color', Sdf.ValueTypeNames.Color3f),
        "SheenRoughness":('sheen_roughness', Sdf.ValueTypeNames.Float),
        "SpecularWeight":('specular', Sdf.ValueTypeNames.Float),
        "Anisotropy":('specular_anisotropy', Sdf.ValueTypeNames.Float),
        "SpecularColor":('specular_color', Sdf.ValueTypeNames.Color3f),
        "SpecularIOR":('specular_IOR', Sdf.ValueTypeNames.Float),
        "Rotation":('specular_rotation', Sdf.ValueTypeNames.Float),
        "SpecularRoughness":('specular_roughness', Sdf.ValueTypeNames.Float),
        "SSSWeight":('subsurface', Sdf.ValueTypeNames.Float),
#        ('subsurface_anisotropy', Sdf.ValueTypeNames.Float),
        "SSSColor":('subsurface_color', Sdf.ValueTypeNames.Color3f),
        "SSSRadius":('subsurface_radius', Sdf.ValueTypeNames.Color3f),
        "SSSScale":('subsurface_scale', Sdf.ValueTypeNames.Float),
#        ('subsurface_type', str),
#        ('tangent', Sdf.ValueTypeNames.Color3f),
        "ThinIOR":('thin_film_IOR', Sdf.ValueTypeNames.Float),
        "ThinThick":('thin_film_thickness', Sdf.ValueTypeNames.Float),
#        ('thin_walled', bool),
        "TransmissionWeight":('transmission', Sdf.ValueTypeNames.Float),
        "TransmissionColor":('transmission_color', Sdf.ValueTypeNames.Color3f),
        "TransmissionDepth":('transmission_depth', Sdf.ValueTypeNames.Float),
        "TransmissionDisp":('transmission_dispersion', Sdf.ValueTypeNames.Float),
        "TransmissionRoughness":('transmission_extra_roughness', Sdf.ValueTypeNames.Float),
        "TransmissionScatter":('transmission_scatter', Sdf.ValueTypeNames.Color3f),
        "TransmissionScatAnis":('transmission_scatter_anisotropy', Sdf.ValueTypeNames.Float),
#        ('transmit_aovs', bool),
        "Bump": (None, None),
        "Vector": (None, None),
        "Displacement": (None, None),
    }
    usdShadeExport._debuglog("Writing USD Arnold Standard Surface shader network for %s" % usd_shader_source.sourceShader().name())
    material_sdf_path = usd_shader.GetPath().GetParentPath()

    shader_model = usd_shader_source.shaderModel()
    export_items = []
    for shader_input_name in shader_model.inputNames():
        usd_shader_input_name, sdf_type = mari_to_usd_input_map[shader_input_name]
        if usd_shader_input_name is None:
            continue
        export_item = usd_shader_source.getInputExportItem(shader_input_name)
        if export_item is not None:

            # TODO: Implement a override option for export that gets passed into this function
            # Perform the texture export
            # if not hasExportItemBeenExported(export_item, export_root_path):
            #     mari.exports.exportTextures([export_item], export_root_path)

            # Create and connect the texture reading shading node
            texture_usd_file_name = re.sub(r"\$UDIM", "<UDIM>", export_item.resolveFileTemplate())
            texture_usd_file_path = os.path.join(usd_export_parameters.exportRootPath(), texture_usd_file_name)
            texture_sampler_sdf_path = material_sdf_path.AppendChild("{0}Texture".format(shader_input_name))
            texture_sampler = UsdShade.Shader.Define(looks_stage, texture_sampler_sdf_path)
            texture_sampler.CreateIdAttr("image") # Arnold standard_surface uses image instead of UsdUVTexture although UsdUVTexture is compatible
            usd_shader.CreateInput(usd_shader_input_name, sdf_type).ConnectToSource(
                texture_sampler.ConnectableAPI(),
                usdShadeExport.colorComponentForType(sdf_type)
            )
            texture_sampler.CreateInput("filename", Sdf.ValueTypeNames.Asset).Set(texture_usd_file_path)

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
        mari.exports.exportTextures(export_items, usd_export_parameters.exportRootPath())

if mari.app.isRunning():
    usdShadeExport.registerRendererExportPlugin(
        "Arnold Standard Surface",
        "standard_surface",
        writeArnoldStandardSurface,
        "out",
        None
    )