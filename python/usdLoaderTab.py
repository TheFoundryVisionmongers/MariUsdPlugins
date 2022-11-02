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
import PySide2.QtCore as core
import PySide2.QtWidgets as widgets
qt = core.Qt

class UsdLoaderWidget(widgets.QWidget):
    def __init__(self, parent = None):
        widgets.QWidget.__init__(self, parent = parent)

        layout = widgets.QFormLayout()
        layout.setSpacing(10)
        self.setLayout(layout)

        self.load_box = widgets.QComboBox()
        self.load_box.setToolTip("""Specify the mode for loading models from the USD file
  - First Found : Load only the model found first in the file
  - All Models : Load all the models found in the file
  - Specified Models in Model Names : Load only the models specified in the Model Names field""")
        layout.addRow("Load",self.load_box)

        self.merge_type_box = widgets.QComboBox()
        self.merge_type_box.setToolTip("""Specify whether to merge the models in the file into a single Object
  - Merge Models : Merge the models into a single Object
  - Keep Models Separate : Keep the models separate""")
        layout.addRow("Merge Type",self.merge_type_box)

        self.model_names_edit = widgets.QLineEdit()
        self.model_names_edit.setToolTip('''Specify the list of models by providing a comma separated list of model names. This is effective only if the Load option is set to "Specified Models in Model Names"''')
        layout.addRow("Model Names", self.model_names_edit)

        self.uv_set_box = widgets.QComboBox()
        self.uv_set_box.setToolTip("""Specify the UV set to load""")
        layout.addRow("UV Set", self.uv_set_box)

        self.mapping_scheme_box = widgets.QComboBox()
        self.mapping_scheme_box.setToolTip("""Specify the mode for UV layout
  - UV if available, Ptex otherwise : Load the UV layout if available. If there is no UV layout, Ptex texture is created
  - Force Ptex : Force to create Ptex texture no matter if there is UV layout""")
        layout.addRow("Mapping Scheme", self.mapping_scheme_box)

        self.frame_numbers_edit = widgets.QLineEdit()
        self.frame_numbers_edit.setToolTip("""Specify the frame numbers to load""")
        self.frame_numbers_edit.setText("1")
        layout.addRow("Frame Numbers", self.frame_numbers_edit)

        self.gprim_names_edit = widgets.QLineEdit()
        self.gprim_names_edit.setToolTip("""Specify the list of models by providing a comma separated list of paths of model prims.""")
        layout.addRow("Gprim Names", self.gprim_names_edit)

        self.variants_edit = widgets.QLineEdit()
        self.variants_edit.setToolTip("""Specify the list of variants to load by providing a space separated list of valid SdfPath string representation that specifies variants
e.g. A valid SdfPath string representation is /path/to/prim{variant_set_name=variant_name}""")
        layout.addRow("Variants", self.variants_edit)

        self.keep_centered_checkbox = widgets.QCheckBox()
        self.keep_centered_checkbox.setToolTip("""Check to discard model transforms and keep everything centered""")
        layout.addRow("Keep Centered", self.keep_centered_checkbox)

        self.conform_y_up_checkbox = widgets.QCheckBox()
        self.conform_y_up_checkbox.setToolTip("""Check to alter the model orientation to conform to Mari's Y as up""")
        self.conform_y_up_checkbox.setChecked(True)
        layout.addRow("Conform to Mari Y as up", self.conform_y_up_checkbox)

        self.include_invisible_checkbox = widgets.QCheckBox()
        self.include_invisible_checkbox.setToolTip("""Check to load invisible models""")
        layout.addRow("Include Invisible", self.include_invisible_checkbox)

        self.create_face_selection_group_checkbox = widgets.QCheckBox()
        self.create_face_selection_group_checkbox.setToolTip("""Check to create selection groups per mesh""")
        layout.addRow("Create Face Selection Group per mesh", self.create_face_selection_group_checkbox)

    def showEvent(self, event):
        attr = mari.app.getGeoPluginAttribute("Load")
        self.load_box.clear()
        self.load_box.addItems(attr.splitlines())
        self.load_box.setCurrentIndex(1)

        attr = mari.app.getGeoPluginAttribute("Merge Type")
        self.merge_type_box.clear()
        self.merge_type_box.addItems(attr.splitlines())

        attr = mari.app.getGeoPluginAttribute("Mapping Scheme")
        self.mapping_scheme_box.clear()
        self.mapping_scheme_box.addItems(attr.splitlines())

        # Update the UV Set input dynamically on showEvent to respond to the valuesin the USD file.
        attr = mari.app.getGeoPluginAttribute("UV Set")
        self.uv_set_box.clear()
        [self.uv_set_box.addItem(line) for line in attr.splitlines()]

    def hideEvent(self, event):
        mari.app.setGeoPluginAttribute("Load", self.load_box.currentText())
        mari.app.setGeoPluginAttribute("Merge Type", self.merge_type_box.currentText())
        mari.app.setGeoPluginAttribute("Model Names", self.model_names_edit.text())
        mari.app.setGeoPluginAttribute("UV Set", self.uv_set_box.currentText())
        mari.app.setGeoPluginAttribute("Mapping Scheme", self.mapping_scheme_box.currentText())
        mari.app.setGeoPluginAttribute("Frame Numbers", self.frame_numbers_edit.text())
        mari.app.setGeoPluginAttribute("Gprim Names", self.gprim_names_edit.text())
        mari.app.setGeoPluginAttribute("Variants", self.variants_edit.text())
        mari.app.setGeoPluginAttribute("Keep Centered", self.keep_centered_checkbox.checkState() == qt.Checked)
        mari.app.setGeoPluginAttribute("Conform to Mari Y as up", self.conform_y_up_checkbox.checkState() == qt.Checked)
        mari.app.setGeoPluginAttribute("Include Invisible", self.include_invisible_checkbox.checkState() == qt.Checked)
        mari.app.setGeoPluginAttribute("Create Face Selection Group per mesh", self.create_face_selection_group_checkbox.checkState() == qt.Checked)

usd_loader_widget = UsdLoaderWidget()
if mari.app.isRunning():
    mari.app.registerGeoPluginWidget(["usda", "usdc", "usdz", "usd"], usd_loader_widget)

