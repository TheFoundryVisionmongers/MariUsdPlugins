# Copyright 2022 Foundry
#
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification; you may not use this file except in
# compliance with the Apache License and the following modification to it:
# Section 6. Trademarks. is deleted and replaced with:
#
# 6. Trademarks. This License does not grant permission to use the trade
#    names, trademarks, service marks, or product names of the Licensor
#    and its affiliates, except as required to comply with Section 4(c) of
#    the License and to reproduce the content of the NOTICE file.
#
# You may obtain a copy of the Apache License at
#
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.

import mari
import os
import re
import PySide2.QtWidgets as widgets
from . import usdShadeExport
from pxr import Sdf, UsdShade

PRMAN_SETTINGS_GROUP = "PRManUSDExportSettings"
PRMAN_SETTING_POSTPROCESS = "PostProcessCommand"

PRMAN_DEFAULT_SETTINGS = {
    PRMAN_SETTING_POSTPROCESS: "txmake $EXPORTED $POSTPROCESSED"
}

def colorComponentForType(sdf_type):
    if sdf_type == Sdf.ValueTypeNames.Color3f:
        return "resultRGB"
    elif sdf_type == Sdf.ValueTypeNames.Normal3f:
        return "resultN"
    elif sdf_type == Sdf.ValueTypeNames.Float:
        return "resultR"
    return "resultRGB"

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
        #"shadowBumpTerminator"                : ('shadowBumpTerminator', Sdf.ValueTypeNames.Int),
        "shadowColor"                         : ('shadowColor', Sdf.ValueTypeNames.Vector3f),
        #"shadowMode"                          : ('shadowMode', Sdf.ValueTypeNames.Int),
        "presence"                            : ('presence', Sdf.ValueTypeNames.Float),
        #"presenceCached"                      : ('presenceCached', Sdf.ValueTypeNames.Int),
        #"mwStartable"                         : ('mwStartable', Sdf.ValueTypeNames.Int),
        #"roughnessMollificationClamp"         : ('roughnessMollificationClamp', Sdf.ValueTypeNames.Float),
        #"userColor"                           : ('userColor', Sdf.ValueTypeNames.Vector3f),
        #"utilityPattern"                      : ('utilityPattern', Sdf.ValueTypeNames.IntArray),
        "Bump"                                : ('bumpNormal', Sdf.ValueTypeNames.Normal3f),
        "Normal"                              : ('bumpNormal', Sdf.ValueTypeNames.Normal3f),
        "Vector"                              : (None, None),
        "Displacement"                        : (None, None)
    }
    usdShadeExport._debuglog("Writing Pxr Surface shader network for %s" % usd_shader_source.sourceShader().name())
    material_sdf_path = usd_shader.GetPath().GetParentPath()

    shader_model = usd_shader_source.shaderModel()
    source_shader = usd_shader_source.sourceShader()
    node_prefix = source_shader.name().replace(" ","_")
    export_items = []
    bump_sampler = None
    normal_sampler = None
    for shader_input_name in shader_model.inputNames():
        usd_shader_input_name, sdf_type = mari_to_usd_input_map.get(shader_input_name, (None, None))
        if usd_shader_input_name is None:
            continue
        export_item = usd_shader_source.getInputExportItem(shader_input_name)
        if export_item is not None and export_item.exportEnabled():

            # TODO: Implement a override option for export that gets passed into this function
            # Perform the texture export
            # if not hasExportItemBeenExported(export_item, export_root_path):
            #     mari.exports.exportTextures([export_item], export_root_path)

            # Create and connect the texture reading shading node
            if len(export_item.postProcessedFileTemplate())==0:
                texture_usd_file_name = re.sub(r"\$UDIM", "<UDIM>", export_item.resolveFileTemplate())
            else:
                texture_usd_file_name = re.sub(r"\$UDIM", "<UDIM>", export_item.resolvePostProcessedFileTemplate())
            texture_usd_file_path = os.path.join(usd_export_parameters.exportRootPath(), texture_usd_file_name)
            texture_sampler_sdf_path = material_sdf_path.AppendChild("{0}_{1}Texture".format(node_prefix,shader_input_name))
            texture_sampler = UsdShade.Shader.Define(looks_stage, texture_sampler_sdf_path)
            if sdf_type == Sdf.ValueTypeNames.Normal3f:
                if shader_input_name=="Bump":
                    texture_sampler.CreateIdAttr("PxrTexture")

                    mixer_path = material_sdf_path.AppendChild("{0}_BumpMixer".format(node_prefix))
                    bump_sampler = UsdShade.Shader.Define(looks_stage, mixer_path)
                    bump_sampler.CreateIdAttr("PxrBumpMixer")

                    # store Mari's bump weight in the amount input on the first surface gradient on the PxrBumpMixer node
                    bump_scale = source_shader.getParameter("BumpWeight")
                    bump_sampler.CreateInput("amount1", Sdf.ValueTypeNames.Float).Set(bump_scale)

                    # Attach the PxrTexture to the first surface gradient input on the PxrBumpMixer node
                    bump_sampler.CreateInput("surfaceGradient1", Sdf.ValueTypeNames.Vector3f).ConnectToSource(
                        texture_sampler.ConnectableAPI(),
                        "resultNG"
                    )
                elif shader_input_name=="Normal":
                    texture_sampler.CreateIdAttr("PxrNormalMap")
                    normal_sampler = texture_sampler
                else:
                    print("Unsupported Normal3f sdf_type")
            else:
                texture_sampler.CreateIdAttr("PxrTexture")
                usd_shader.CreateInput(usd_shader_input_name, sdf_type).ConnectToSource(
                    texture_sampler.ConnectableAPI(),
                    colorComponentForType(sdf_type)
                )
            texture_sampler.CreateInput("filename", Sdf.ValueTypeNames.Asset).Set(texture_usd_file_path)

            if usd_shader_source.uvSetName()!="st":
                # If the UV set name is not st, then we need to create the PxrManifold2D node to specify the UV set name
                manifold_sdf_path = material_sdf_path.AppendChild("{0}_{1}TextureManifold".format(node_prefix,shader_input_name))
                manifold = UsdShade.Shader.Define(looks_stage, manifold_sdf_path)
                manifold.CreateIdAttr("PxrManifold2D")
                manifold.CreateInput("name_uvSet", Sdf.ValueTypeNames.String).Set(usd_shader_source.uvSetName())
                texture_sampler.CreateInput("manifold", Sdf.ValueTypeNames.Token).ConnectToSource(
                        manifold.ConnectableAPI(),
                        "result"
                    )

            export_items.append(export_item)
        else:
            if shader_input_name not in source_shader.parameterNameList():
                continue
            input_value = source_shader.getParameter(shader_input_name)
            default_color = shader_model.input(shader_input_name).defaultColor()

            if not usdShadeExport.isValueDefault(input_value, default_color):
                usd_shader_parameter = usd_shader.CreateInput(usd_shader_input_name, sdf_type)
                usd_shader_parameter.Set(usdShadeExport.valueAsShaderParameter(input_value, sdf_type))

    # Bump and Normal need to be combined, so treated specifically
    if bump_sampler:
        if normal_sampler:
            # We have both Normal and Bump. Combine them. i.e. connect Normal to the bumpNormal input of PxrSurface and connect Bump to the bumpOverlay input of PxrNormalMap
            usd_shader.CreateInput("bumpNormal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(
                normal_sampler.ConnectableAPI(),
                colorComponentForType(Sdf.ValueTypeNames.Normal3f)
            )
            normal_sampler.CreateInput("bumpOverlay", Sdf.ValueTypeNames.Normal3f).ConnectToSource(
                bump_sampler.ConnectableAPI(),
                colorComponentForType(Sdf.ValueTypeNames.Normal3f)
            )
        else:
            # We have only Bump
            usd_shader.CreateInput("bumpNormal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(
                bump_sampler.ConnectableAPI(),
                colorComponentForType(Sdf.ValueTypeNames.Normal3f)
            )
    elif normal_sampler:
        # We have only Normal
        usd_shader.CreateInput("bumpNormal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(
            normal_sampler.ConnectableAPI(),
            colorComponentForType(Sdf.ValueTypeNames.Normal3f)
        )

    # Export textures from export items
    if export_items:
        usdShadeExport._debuglog(
            "Exporting %d export items for %s to %s" % (
                len(export_items),
                source_shader.name(),
                usd_export_parameters.exportRootPath()
            )
        )
        mari.exports.exportTextures(export_items, usd_export_parameters.exportRootPath(), usd_export_parameters.exportOverrides(), ShowProgressDialog = True)

class PRMan_SettingsWidget(widgets.QWidget):
    def __init__(self, parent = None):
        widgets.QWidget.__init__(self, parent)
        
        settings = mari.Settings()
        settings.beginGroup(PRMAN_SETTINGS_GROUP)
        post_process_command = settings.value(PRMAN_SETTING_POSTPROCESS, PRMAN_DEFAULT_SETTINGS[PRMAN_SETTING_POSTPROCESS])
        settings.endGroup()
        
        main_layout = widgets.QVBoxLayout()
        post_process_layout = widgets.QHBoxLayout()
        post_process_layout.addWidget(widgets.QLabel("Default Post Process Command"))
        self.post_process_editbox = widgets.QLineEdit()
        self.post_process_editbox.setText(post_process_command)
        self.post_process_editbox.editingFinished.connect(self.onPostProcessCommandEdited)
        post_process_layout.addWidget(self.post_process_editbox)
        main_layout.addLayout(post_process_layout)
        
        self.setLayout(main_layout)
        
    def onPostProcessCommandEdited(self):
        settings = mari.Settings()
        settings.beginGroup(PRMAN_SETTINGS_GROUP)
        value = self.post_process_editbox.text()
        settings.setValue(PRMAN_SETTING_POSTPROCESS, value)
        settings.endGroup()

def PRMan_Callback_SettingsWidget():
    return PRMan_SettingsWidget()

def PRMan_Callback_SetupExportItem(export_item):
    if not isinstance(export_item, mari.ExportItem):
        print("Invalid Export Item received for PRMax SetupExportItem callback.")
        return
    
    settings = mari.Settings()
    settings.beginGroup(PRMAN_SETTINGS_GROUP)
    post_process_command = settings.value(PRMAN_SETTING_POSTPROCESS, PRMAN_DEFAULT_SETTINGS[PRMAN_SETTING_POSTPROCESS])
    settings.endGroup()

    previous_default_post_process_command = None
    if export_item.hasMetadata("PreviousDefaultPostProcessCommand"):
        previous_default_post_process_command = export_item.metadata("PreviousDefaultPostProcessCommand")
    
    # If the existing post process command is the same as the previous command then, assume that the post process command is not individually customized. Apply the default command change
    if previous_default_post_process_command==None or previous_default_post_process_command==export_item.postProcessCommand():
        export_item.setPostProcessCommand(post_process_command)
        template = export_item.fileTemplate()
        basepath = os.path.splitext(template)[0]
        export_item.setPostProcessedFileTemplate(basepath+".tex")

    # Record the default post process command for the next time
    export_item.setMetadata("PreviousDefaultPostProcessCommand", post_process_command)

if mari.app.isRunning():
    callback_functions = {
        usdShadeExport.CALLBACK_NAME_SETUP_EXPORT_ITEM:  PRMan_Callback_SetupExportItem,
        usdShadeExport.CALLBACK_NAME_EXPORT_EXPORT_ITEM: None,
        usdShadeExport.CALLBACK_NAME_SETTINGS_WIDGET:    PRMan_Callback_SettingsWidget
    }
    
    usdShadeExport.registerRendererExportPlugin(
        "PxrSurface",
        "PxrSurface",
        writePrManSurface,
        "out",
        "ri",
        callback_functions
    )
