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

ARNOLD_SETTINGS_GROUP = "ArnoldUSDExportSettings"
ARNOLD_SETTING_POSTPROCESS = "PostProcessCommand"

ARNOLD_DEFAULT_SETTINGS = {
    ARNOLD_SETTING_POSTPROCESS: "maketx $EXPORTED $POSTPROCESSED"
}

def colorsFuzzyEqual(color0, color1):
    for i in range(4):
        if abs(color0[i]-color1[i])>0.003:
            return False
    return True

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
            export_items.append(export_item)

    # Export textures from export items
    if export_items:
        usdShadeExport._debuglog(
            "Exporting %d export items for %s to %s" % (
                len(export_items),
                usd_shader_source.sourceShader().name(),
                usd_export_parameters.exportRootPath()
            )
        )
        mari.exports.exportTextures(export_items, usd_export_parameters.exportRootPath(), ShowProgressDialog = True)

    for shader_input_name in shader_model.inputNames():
        usd_shader_input_name, sdf_type = mari_to_usd_input_map[shader_input_name]
        if usd_shader_input_name is None:
            continue

        if shader_input_name not in usd_shader_source.sourceShader().parameterNameList():
            continue

        input_value = usd_shader_source.sourceShader().getParameter(shader_input_name)
        default_color = usd_shader_source.shaderModel().input(shader_input_name).defaultColor()

        export_item = usd_shader_source.getInputExportItem(shader_input_name)

        assign_texture = False
        if export_item:
            if export_item.exportedImagesUniform():
                exported_uniform_color = export_item.exportedImagesUniformColor().rgba()
                if exported_uniform_color != mari.Color(0,0,0,0).rgba() and not colorsFuzzyEqual(exported_uniform_color, default_color.rgba()):
                    assign_texture = True
            else:
                assign_texture = True

        if assign_texture:

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
            texture_sampler_sdf_path = material_sdf_path.AppendChild("{0}Texture".format(shader_input_name))
            texture_sampler = UsdShade.Shader.Define(looks_stage, texture_sampler_sdf_path)
            texture_sampler.CreateIdAttr("image") # Arnold standard_surface uses image instead of UsdUVTexture although UsdUVTexture is compatible
            usd_shader.CreateInput(usd_shader_input_name, sdf_type).ConnectToSource(
                texture_sampler.ConnectableAPI(),
                usdShadeExport.colorComponentForType(sdf_type)
            )
            texture_sampler.CreateInput("filename", Sdf.ValueTypeNames.Asset).Set(texture_usd_file_path)
        else:
            if not usdShadeExport.isValueDefault(input_value, default_color):
                usd_shader_parameter = usd_shader.CreateInput(usd_shader_input_name, sdf_type)
                usd_shader_parameter.Set(usdShadeExport.valueAsShaderParameter(input_value, sdf_type))

class Arnold_SettingsWidget(widgets.QWidget):
    def __init__(self, parent = None):
        widgets.QWidget.__init__(self, parent)
        
        settings = mari.Settings()
        settings.beginGroup(ARNOLD_SETTINGS_GROUP)
        post_process_command = settings.value(ARNOLD_SETTING_POSTPROCESS, ARNOLD_DEFAULT_SETTINGS[ARNOLD_SETTING_POSTPROCESS])
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
        settings.beginGroup(ARNOLD_SETTINGS_GROUP)
        value = self.post_process_editbox.text()
        settings.setValue(ARNOLD_SETTING_POSTPROCESS, value)
        settings.endGroup()

def Arnold_Callback_SettingsWidget():
    return Arnold_SettingsWidget()

def Arnold_Callback_SetupExportItem(export_item):
    if not isinstance(export_item, mari.ExportItem):
        print("Invalid Export Item received for Arnold SetupExportItem callback.")
        return
    
    settings = mari.Settings()
    settings.beginGroup(ARNOLD_SETTINGS_GROUP)
    post_process_command = settings.value(ARNOLD_SETTING_POSTPROCESS, ARNOLD_DEFAULT_SETTINGS[ARNOLD_SETTING_POSTPROCESS])
    settings.endGroup()
    
    export_item.setPostProcessCommand(post_process_command)
    template = export_item.fileTemplate()
    basepath = os.path.splitext(template)[0]
    export_item.setPostProcessedFileTemplate(basepath+".tx")

if mari.app.isRunning():
    callback_functions = {
        usdShadeExport.CALLBACK_NAME_SETUP_EXPORT_ITEM:  Arnold_Callback_SetupExportItem,
        usdShadeExport.CALLBACK_NAME_EXPORT_EXPORT_ITEM: None,
        usdShadeExport.CALLBACK_NAME_SETTINGS_WIDGET:    Arnold_Callback_SettingsWidget
    }
    
    usdShadeExport.registerRendererExportPlugin(
        "Arnold Standard Surface",
        "standard_surface",
        writeArnoldStandardSurface,
        "out",
        None,
        callback_functions
    )
