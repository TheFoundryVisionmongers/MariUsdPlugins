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
from fnpxr import Sdf, UsdShade

PRINCIPLED_BRDF_SETTINGS_GROUP = "PrincipledBRDFUSDExportSettings"
PRINCIPLED_BRDF_SETTING_POSTPROCESS = "PostProcessCommand"

PRINCIPLED_BRDF_DEFAULT_SETTINGS = {
    PRINCIPLED_BRDF_SETTING_POSTPROCESS: "txmake $EXPORTED $EXPORTDIR/$EXPORTBASE.tx"
}

def colorComponentForType(sdf_type):
    if sdf_type == Sdf.ValueTypeNames.Color3f:
        return "resultRGB"
    elif sdf_type == Sdf.ValueTypeNames.Normal3f:
        return "resultN"
    elif sdf_type == Sdf.ValueTypeNames.Float:
        return "resultR"
    return "resultRGB"

def writePrincipledBRDFSurface(looks_stage, usd_shader, usd_export_parameters, usd_shader_source):
    """Function to write out the Usd shading nodes for an input to an PxrSurface shader.

    Args:
        looks_stage (Usd.Stage): Stage to write to
        usd_shader (Usd.Shader): Shader to connect to
        usd_export_parameters (UsdExportParameters): Container for export parameters
        usd_shader_source (UsdShaderSource): Container of source Shader and Export Item instances
    """
    mari_to_usd_input_map = {
        "BaseColor":('baseColor', Sdf.ValueTypeNames.Color3f),
        "EmissiveColor":('emitColor', Sdf.ValueTypeNames.Color3f),
        "subsurface":('subsurface', Sdf.ValueTypeNames.Float),
#        ('subsurfaceColor', Sdf.ValueTypeNames.Color3f),
        "metallic":('metallic', Sdf.ValueTypeNames.Float),
        "specular":('specular', Sdf.ValueTypeNames.Float),
        "specularTint":('specularTint', Sdf.ValueTypeNames.Float),
        "roughness":('roughness', Sdf.ValueTypeNames.Float),
        "anisotropic":('anisotropic', Sdf.ValueTypeNames.Float),
        "sheen":('sheen', Sdf.ValueTypeNames.Float),
        "sheenTint":('sheenTint', Sdf.ValueTypeNames.Float),
        "clearcoat":('clearcoat', Sdf.ValueTypeNames.Float),
        "clearcoatGloss":('clearcoatGloss', Sdf.ValueTypeNames.Float),
        "Normal":('bumpNormal', Sdf.ValueTypeNames.Normal3f),
#        ('shadowBumpTerminator', <type 'int'>),
#        ('presence', Sdf.ValueTypeNames.Float),
#        ('inputAOV', <type 'int'>),
    }
    usdShadeExport._debuglog("Writing Principled BRDF shader network for %s" % usd_shader_source.sourceShader().name())
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
            if sdf_type == Sdf.ValueTypeNames.Normal3f:
                texture_sampler.CreateIdAttr("PxrNormalMap")
            else:
                texture_sampler.CreateIdAttr("PxrTexture")
            usd_shader.CreateInput(usd_shader_input_name, sdf_type).ConnectToSource(
                texture_sampler.ConnectableAPI(),
                colorComponentForType(sdf_type)
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

class Principled_BRDF_SettingsWidget(widgets.QWidget):
    def __init__(self, parent = None):
        widgets.QWidget.__init__(self, parent)
        
        settings = mari.Settings()
        settings.beginGroup(PRINCIPLED_BRDF_SETTINGS_GROUP)
        post_process_command = settings.value(PRINCIPLED_BRDF_SETTING_POSTPROCESS, PRINCIPLED_BRDF_DEFAULT_SETTINGS[PRINCIPLED_BRDF_SETTING_POSTPROCESS])
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
        settings.beginGroup(PRINCIPLED_BRDF_SETTINGS_GROUP)
        value = self.post_process_editbox.text()
        settings.setValue(PRINCIPLED_BRDF_SETTING_POSTPROCESS, value)
        settings.endGroup()

def Principled_BRDF_Callback_SettingsWidget():
    return Principled_BRDF_SettingsWidget()

def Principled_BRDF_Callback_SetupExportItem(export_item):
    if not isinstance(export_item, mari.ExportItem):
        print("Invalid Export Item received for Principled BRDF SetupExportItem callback.")
        return
    
    settings = mari.Settings()
    settings.beginGroup(PRINCIPLED_BRDF_SETTINGS_GROUP)
    post_process_command = settings.value(PRINCIPLED_BRDF_SETTING_POSTPROCESS, PRINCIPLED_BRDF_DEFAULT_SETTINGS[PRINCIPLED_BRDF_SETTING_POSTPROCESS])
    settings.endGroup()
    
    export_item.setPostProcessCommand(post_process_command)

if mari.app.isRunning():
    callback_functions = {
        usdShadeExport.CALLBACK_NAME_SETUP_EXPORT_ITEM:  Principled_BRDF_Callback_SetupExportItem,
        usdShadeExport.CALLBACK_NAME_EXPORT_EXPORT_ITEM: Principled_BRDF_Callback_SetupExportItem,
        usdShadeExport.CALLBACK_NAME_SETTINGS_WIDGET:    Principled_BRDF_Callback_SettingsWidget
    }
   
    usdShadeExport.registerRendererExportPlugin(
        "Principled BRDF",
        "PxrDisney",
        writePrincipledBRDFSurface,
        "out",
        None,
        callback_functions
    )
