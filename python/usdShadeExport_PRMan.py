import mari
import os
import re
from . import usdShadeExport
from pxr import Sdf, UsdShade

def writePrManSurface(looks_stage, usd_shader, usd_export_parameters, usd_shader_source):
    """Function to write out the Usd shading nodes for an input to an PxrSurface shader.

    Args:
        looks_stage (Usd.Stage): Stage to write to
        usd_shader (Usd.Shader): Shader to connect to
        usd_export_parameters (UsdExportParameters): Container for export parameters
        usd_shader_source (UsdShaderSource): Container of source Shader and Export Item instances
    """
    mari_to_usd_input_map = {
        "inputMaterial"                       : ('inputMaterial', Sdf.ValueTypeNames.String),
        "diffuseGain"                         : ('diffuseGain', Sdf.ValueTypeNames.Float),
        "diffuseColor"                        : ('diffuseColor', Sdf.ValueTypeNames.Vector3f),
        "diffuseRoughness"                    : ('diffuseRoughness', Sdf.ValueTypeNames.Float),
        "diffuseExponent"                     : ('diffuseExponent', Sdf.ValueTypeNames.Float),
        #"diffuseBumpNormal"                   : ('diffuseBumpNormal', Sdf.ValueTypeNames.Vector3f),
        "diffuseDoubleSided"                  : ('diffuseDoubleSided', Sdf.ValueTypeNames.Int),
        "diffuseBackUseDiffuseColor"          : ('diffuseBackUseDiffuseColor', Sdf.ValueTypeNames.Int),
        "diffuseBackColor"                    : ('diffuseBackColor', Sdf.ValueTypeNames.Vector3f),
        "diffuseTransmitGain"                 : ('diffuseTransmitGain', Sdf.ValueTypeNames.Float),
        "diffuseTransmitColor"                : ('diffuseTransmitColor', Sdf.ValueTypeNames.Vector3f),
        "specularFresnelMode"                 : ('specularFresnelMode', Sdf.ValueTypeNames.Int),
        "specularFaceColor"                   : ('specularFaceColor', Sdf.ValueTypeNames.Vector3f),
        "specularEdgeColor"                   : ('specularEdgeColor', Sdf.ValueTypeNames.Vector3f),
        "specularFresnelShape"                : ('specularFresnelShape', Sdf.ValueTypeNames.Float),
        "specularIor"                         : ('specularIor', Sdf.ValueTypeNames.Vector3f),
        "specularExtinctionCoeff"             : ('specularExtinctionCoeff', Sdf.ValueTypeNames.Vector3f),
        "specularRoughness"                   : ('specularRoughness', Sdf.ValueTypeNames.Float),
        "specularModelType"                   : ('specularModelType', Sdf.ValueTypeNames.Int),
        "specularAnisotropy"                  : ('specularAnisotropy', Sdf.ValueTypeNames.Float),
        "specularAnisotropyDirection"         : ('specularAnisotropyDirection', Sdf.ValueTypeNames.Vector3f),
        #"specularBumpNormal"                  : ('specularBumpNormal', Sdf.ValueTypeNames.Vector3f),
        "specularDoubleSided"                 : ('specularDoubleSided', Sdf.ValueTypeNames.Int),
        "roughSpecularFresnelMode"            : ('roughSpecularFresnelMode', Sdf.ValueTypeNames.Int),
        "roughSpecularFaceColor"              : ('roughSpecularFaceColor', Sdf.ValueTypeNames.Vector3f),
        "roughSpecularEdgeColor"              : ('roughSpecularEdgeColor', Sdf.ValueTypeNames.Vector3f),
        "roughSpecularFresnelShape"           : ('roughSpecularFresnelShape', Sdf.ValueTypeNames.Float),
        "roughSpecularIor"                    : ('roughSpecularIor', Sdf.ValueTypeNames.Vector3f),
        "roughSpecularExtinctionCoeff"        : ('roughSpecularExtinctionCoeff', Sdf.ValueTypeNames.Vector3f),
        "roughSpecularRoughness"              : ('roughSpecularRoughness', Sdf.ValueTypeNames.Float),
        "roughSpecularModelType"              : ('roughSpecularModelType', Sdf.ValueTypeNames.Int),
        "roughSpecularAnisotropy"             : ('roughSpecularAnisotropy', Sdf.ValueTypeNames.Float),
        "roughSpecularAnisotropyDirection"    : ('roughSpecularAnisotropyDirection', Sdf.ValueTypeNames.Vector3f),
        #"roughSpecularBumpNormal"             : ('roughSpecularBumpNormal', Sdf.ValueTypeNames.Vector3f),
        "roughSpecularDoubleSided"            : ('roughSpecularDoubleSided', Sdf.ValueTypeNames.Int),
        "clearcoatFresnelMode"                : ('clearcoatFresnelMode', Sdf.ValueTypeNames.Int),
        "clearcoatFaceColor"                  : ('clearcoatFaceColor', Sdf.ValueTypeNames.Vector3f),
        "clearcoatEdgeColor"                  : ('clearcoatEdgeColor', Sdf.ValueTypeNames.Vector3f),
        "clearcoatFresnelShape"               : ('clearcoatFresnelShape', Sdf.ValueTypeNames.Float),
        "clearcoatIor"                        : ('clearcoatIor', Sdf.ValueTypeNames.Vector3f),
        "clearcoatExtinctionCoeff"            : ('clearcoatExtinctionCoeff', Sdf.ValueTypeNames.Vector3f),
        "clearcoatThickness"                  : ('clearcoatThickness', Sdf.ValueTypeNames.Float),
        "clearcoatAbsorptionTint"             : ('clearcoatAbsorptionTint', Sdf.ValueTypeNames.Vector3f),
        "clearcoatRoughness"                  : ('clearcoatRoughness', Sdf.ValueTypeNames.Float),
        "clearcoatModelType"                  : ('clearcoatModelType', Sdf.ValueTypeNames.Int),
        "clearcoatAnisotropy"                 : ('clearcoatAnisotropy', Sdf.ValueTypeNames.Float),
        "clearcoatAnisotropyDirection"        : ('clearcoatAnisotropyDirection', Sdf.ValueTypeNames.Vector3f),
        #"clearcoatBumpNormal"                 : ('clearcoatBumpNormal', Sdf.ValueTypeNames.Vector3f),
        "clearcoatDoubleSided"                : ('clearcoatDoubleSided', Sdf.ValueTypeNames.Int),
        "specularEnergyCompensation"          : ('specularEnergyCompensation', Sdf.ValueTypeNames.Float),
        "clearcoatEnergyCompensation"         : ('clearcoatEnergyCompensation', Sdf.ValueTypeNames.Float),
        "iridescenceFaceGain"                 : ('iridescenceFaceGain', Sdf.ValueTypeNames.Float),
        "iridescenceEdgeGain"                 : ('iridescenceEdgeGain', Sdf.ValueTypeNames.Float),
        "iridescenceFresnelShape"             : ('iridescenceFresnelShape', Sdf.ValueTypeNames.Float),
        "iridescenceMode"                     : ('iridescenceMode', Sdf.ValueTypeNames.Int),
        "iridescencePrimaryColor"             : ('iridescencePrimaryColor', Sdf.ValueTypeNames.Vector3f),
        "iridescenceSecondaryColor"           : ('iridescenceSecondaryColor', Sdf.ValueTypeNames.Vector3f),
        "iridescenceRoughness"                : ('iridescenceRoughness', Sdf.ValueTypeNames.Float),
        "iridescenceAnisotropy"               : ('iridescenceAnisotropy', Sdf.ValueTypeNames.Float),
        "iridescenceAnisotropyDirection"      : ('iridescenceAnisotropyDirection', Sdf.ValueTypeNames.Vector3f),
        #"iridescenceBumpNormal"               : ('iridescenceBumpNormal', Sdf.ValueTypeNames.Vector3f),
        "iridescenceCurve"                    : ('iridescenceCurve', Sdf.ValueTypeNames.Float),
        "iridescenceScale"                    : ('iridescenceScale', Sdf.ValueTypeNames.Float),
        "iridescenceFlip"                     : ('iridescenceFlip', Sdf.ValueTypeNames.Int),
        "iridescenceThickness"                : ('iridescenceThickness', Sdf.ValueTypeNames.Float),
        "iridescenceDoubleSided"              : ('iridescenceDoubleSided', Sdf.ValueTypeNames.Int),
        "fuzzGain"                            : ('fuzzGain', Sdf.ValueTypeNames.Float),
        "fuzzColor"                           : ('fuzzColor', Sdf.ValueTypeNames.Vector3f),
        "fuzzConeAngle"                       : ('fuzzConeAngle', Sdf.ValueTypeNames.Float),
        #"fuzzBumpNormal"                      : ('fuzzBumpNormal', Sdf.ValueTypeNames.Vector3f),
        "fuzzDoubleSided"                     : ('fuzzDoubleSided', Sdf.ValueTypeNames.Int),
        "subsurfaceType"                      : ('subsurfaceType', Sdf.ValueTypeNames.Int),
        "subsurfaceGain"                      : ('subsurfaceGain', Sdf.ValueTypeNames.Float),
        "subsurfaceColor"                     : ('subsurfaceColor', Sdf.ValueTypeNames.Vector3f),
        "subsurfaceDmfp"                      : ('subsurfaceDmfp', Sdf.ValueTypeNames.Float),
        "subsurfaceDmfpColor"                 : ('subsurfaceDmfpColor', Sdf.ValueTypeNames.Vector3f),
        "shortSubsurfaceGain"                 : ('shortSubsurfaceGain', Sdf.ValueTypeNames.Float),
        "shortSubsurfaceColor"                : ('shortSubsurfaceColor', Sdf.ValueTypeNames.Vector3f),
        "shortSubsurfaceDmfp"                 : ('shortSubsurfaceDmfp', Sdf.ValueTypeNames.Float),
        "longSubsurfaceGain"                  : ('longSubsurfaceGain', Sdf.ValueTypeNames.Float),
        "longSubsurfaceColor"                 : ('longSubsurfaceColor', Sdf.ValueTypeNames.Vector3f),
        "longSubsurfaceDmfp"                  : ('longSubsurfaceDmfp', Sdf.ValueTypeNames.Float),
        "subsurfaceDirectionality"            : ('subsurfaceDirectionality', Sdf.ValueTypeNames.Float),
        "subsurfaceBleed"                     : ('subsurfaceBleed', Sdf.ValueTypeNames.Float),
        "subsurfaceDiffuseBlend"              : ('subsurfaceDiffuseBlend', Sdf.ValueTypeNames.Float),
        "subsurfaceResolveSelfIntersections"  : ('subsurfaceResolveSelfIntersections', Sdf.ValueTypeNames.Int),
        "subsurfaceIor"                       : ('subsurfaceIor', Sdf.ValueTypeNames.Float),
        "subsurfacePostTint"                  : ('subsurfacePostTint', Sdf.ValueTypeNames.Vector3f),
        "subsurfaceDiffuseSwitch"             : ('subsurfaceDiffuseSwitch', Sdf.ValueTypeNames.Float),
        "subsurfaceDoubleSided"               : ('subsurfaceDoubleSided', Sdf.ValueTypeNames.Int),
        "subsurfaceTransmitGain"              : ('subsurfaceTransmitGain', Sdf.ValueTypeNames.Float),
        #"considerBackside"                    : ('considerBackside', Sdf.ValueTypeNames.Int),
        #"continuationRayMode"                 : ('continuationRayMode', Sdf.ValueTypeNames.Int),
        #"maxContinuationHits"                 : ('maxContinuationHits', Sdf.ValueTypeNames.Int),
        #"followTopology"                      : ('followTopology', Sdf.ValueTypeNames.Float),
        #"subsurfaceSubset"                    : ('subsurfaceSubset', Sdf.ValueTypeNames.String),
        "singlescatterGain"                   : ('singlescatterGain', Sdf.ValueTypeNames.Float),
        "singlescatterColor"                  : ('singlescatterColor', Sdf.ValueTypeNames.Vector3f),
        "singlescatterMfp"                    : ('singlescatterMfp', Sdf.ValueTypeNames.Float),
        "singlescatterMfpColor"               : ('singlescatterMfpColor', Sdf.ValueTypeNames.Vector3f),
        "singlescatterDirectionality"         : ('singlescatterDirectionality', Sdf.ValueTypeNames.Float),
        "singlescatterIor"                    : ('singlescatterIor', Sdf.ValueTypeNames.Float),
        "singlescatterBlur"                   : ('singlescatterBlur', Sdf.ValueTypeNames.Float),
        "singlescatterDirectGain"             : ('singlescatterDirectGain', Sdf.ValueTypeNames.Float),
        "singlescatterDirectGainTint"         : ('singlescatterDirectGainTint', Sdf.ValueTypeNames.Vector3f),
        "singlescatterDoubleSided"            : ('singlescatterDoubleSided', Sdf.ValueTypeNames.Int),
        "singlescatterConsiderBackside"       : ('singlescatterConsiderBackside', Sdf.ValueTypeNames.Int),
        "singlescatterContinuationRayMode"    : ('singlescatterContinuationRayMode', Sdf.ValueTypeNames.Int),
        "singlescatterMaxContinuationHits"    : ('singlescatterMaxContinuationHits', Sdf.ValueTypeNames.Int),
        "singlescatterDirectGainMode"         : ('singlescatterDirectGainMode', Sdf.ValueTypeNames.Int),
        "singlescatterSubset"                 : ('singlescatterSubset', Sdf.ValueTypeNames.String),
        "irradianceTint"                      : ('irradianceTint', Sdf.ValueTypeNames.Vector3f),
        "irradianceRoughness"                 : ('irradianceRoughness', Sdf.ValueTypeNames.Float),
        #"unitLength"                          : ('unitLength', Sdf.ValueTypeNames.Float),
        "refractionGain"                      : ('refractionGain', Sdf.ValueTypeNames.Float),
        "reflectionGain"                      : ('reflectionGain', Sdf.ValueTypeNames.Float),
        "refractionColor"                     : ('refractionColor', Sdf.ValueTypeNames.Vector3f),
        "glassRoughness"                      : ('glassRoughness', Sdf.ValueTypeNames.Float),
        "glassRefractionRoughness"            : ('glassRefractionRoughness', Sdf.ValueTypeNames.Float),
        "glassAnisotropy"                     : ('glassAnisotropy', Sdf.ValueTypeNames.Float),
        "glassAnisotropyDirection"            : ('glassAnisotropyDirection', Sdf.ValueTypeNames.Vector3f),
        #"glassBumpNormal"                     : ('glassBumpNormal', Sdf.ValueTypeNames.Vector3f),
        "glassIor"                            : ('glassIor', Sdf.ValueTypeNames.Float),
        #"mwWalkable"                          : ('mwWalkable', Sdf.ValueTypeNames.Int),
        #"mwIor"                               : ('mwIor', Sdf.ValueTypeNames.Float),
        #"thinGlass"                           : ('thinGlass', Sdf.ValueTypeNames.Int),
        #"ignoreFresnel"                       : ('ignoreFresnel', Sdf.ValueTypeNames.Int),
        #"ignoreAccumOpacity"                  : ('ignoreAccumOpacity', Sdf.ValueTypeNames.Int),
        #"blocksVolumes"                       : ('blocksVolumes', Sdf.ValueTypeNames.Int),
        #"volumeAggregate"                     : ('volumeAggregate', Sdf.ValueTypeNames.Int),
        #"volumeAggregateName"                 : ('volumeAggregateName', Sdf.ValueTypeNames.String),
        "ssAlbedo"                            : ('ssAlbedo', Sdf.ValueTypeNames.Vector3f),
        "extinction"                          : ('extinction', Sdf.ValueTypeNames.Vector3f),
        #"g0"                                  : ('g0', Sdf.ValueTypeNames.Float),
        #"g1"                                  : ('g1', Sdf.ValueTypeNames.Float),
        #"blend"                               : ('blend', Sdf.ValueTypeNames.Float),
        #"volumeGlow"                          : ('volumeGlow', Sdf.ValueTypeNames.Vector3f),
        #"maxExtinction"                       : ('maxExtinction', Sdf.ValueTypeNames.Float),
        #"multiScatter"                        : ('multiScatter', Sdf.ValueTypeNames.Int),
        #"enableOverlappingVolumes"            : ('enableOverlappingVolumes', Sdf.ValueTypeNames.Int),
        "glowGain"                            : ('glowGain', Sdf.ValueTypeNames.Float),
        "glowColor"                           : ('glowColor', Sdf.ValueTypeNames.Vector3f),
        #"bumpNormal"                          : ('bumpNormal', Sdf.ValueTypeNames.Vector3f),
        #"shadowBumpTerminator"                : ('shadowBumpTerminator', Sdf.ValueTypeNames.Int),
        "shadowColor"                         : ('shadowColor', Sdf.ValueTypeNames.Vector3f),
        #"shadowMode"                          : ('shadowMode', Sdf.ValueTypeNames.Int),
        "presence"                            : ('presence', Sdf.ValueTypeNames.Float),
        #"presenceCached"                      : ('presenceCached', Sdf.ValueTypeNames.Int),
        #"mwStartable"                         : ('mwStartable', Sdf.ValueTypeNames.Int),
        #"roughnessMollificationClamp"         : ('roughnessMollificationClamp', Sdf.ValueTypeNames.Float),
        #"userColor"                           : ('userColor', Sdf.ValueTypeNames.Vector3f),
        #"utilityPattern"                      : ('utilityPattern', Sdf.ValueTypeNames.IntArray),
        "Bump"                                : (None, None),
        "Vector"                              : (None, None),
        "Displacement"                        : (None, None)
    }
    usdShadeExport._debuglog("Writing Pxr Surface shader network for %s" % usd_shader_source.sourceShader().name())
    material_sdf_path = usd_shader.GetPath().GetParentPath()

    shader_model = usd_shader_source.shaderModel()
    source_shader = usd_shader_source.sourceShader()
    export_items = []
    for shader_input_name in shader_model.inputNames():
        usd_shader_input_name, sdf_type = mari_to_usd_input_map.get(shader_input_name, (None, None))
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
            texture_sampler.CreateIdAttr("image")
            usd_shader.CreateInput(usd_shader_input_name, sdf_type).ConnectToSource(
                texture_sampler.ConnectableAPI(),
                usdShadeExport.colorComponentForType(sdf_type)
            )
            texture_sampler.CreateInput("filename", Sdf.ValueTypeNames.Asset).Set(texture_usd_file_path)

            export_items.append(export_item)
        else:
            if shader_input_name not in source_shader.parameterNameList():
                continue
            input_value = source_shader.getParameter(shader_input_name)
            default_color = shader_model.input(shader_input_name).defaultColor()

            if not usdShadeExport.isValueDefault(input_value, default_color):
                usd_shader_parameter = usd_shader.CreateInput(usd_shader_input_name, sdf_type)
                usd_shader_parameter.Set(usdShadeExport.valueAsShaderParameter(input_value, sdf_type))

    # Export textures from export items
    if export_items:
        usdShadeExport._debuglog(
            "Exporting %d export items for %s to %s" % (
                len(export_items),
                source_shader.name(),
                usd_export_parameters.exportRootPath()
            )
        )
        mari.exports.exportTextures(export_items, usd_export_parameters.exportRootPath())

if mari.app.isRunning():
    registerRendererExportPlugin(
    usdShadeExport.registerRendererExportPlugin(
        "PxrSurface",
        "PxrSurface",
        writePrManSurface,
        "out",
        None
    )