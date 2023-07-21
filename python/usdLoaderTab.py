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

from fnpxr import Sdf, Usd, UsdGeom

USER_ROLE_PATH = qt.UserRole

class UsdLoaderTreeWidget(widgets.QTreeWidget):

    def __init__(self, Parent=None):
        widgets.QTreeWidget.__init__(self, Parent)

        self.headerItem().setText(0,"Mesh")

    def populate(self, stage):
        self.clear()
        self._item_map = {}
        for prim in stage.Traverse():
            self._create_tree_node(prim)

    def _create_tree_node(self, prim):
        if not prim.IsA(UsdGeom.Mesh):
            # Support loading only UsdGeom.Mesh type
            return
        prim_path = str(prim.GetPath())
        tree_item = self.invisibleRootItem()
        for token in str(prim_path[1:]).split("/"):
            item_for_token = None
            for i in range(tree_item.childCount()):
                child_item = tree_item.child(i)
                if child_item.text(0)==token:
                    item_for_token = child_item
            if item_for_token==None:
                item_for_token = widgets.QTreeWidgetItem()
                path = tree_item.data(0, USER_ROLE_PATH)
                path = "/"+token if path is None else path+"/"+token
                self._item_map[path] = item_for_token
                item_for_token.setData(0, USER_ROLE_PATH, path)
                item_for_token.setFlags(item_for_token.flags() | qt.ItemIsUserCheckable | qt.ItemIsAutoTristate)
                item_for_token.setCheckState(0, qt.Checked)
                item_for_token.setText(0, token)
                tree_item.addChild(item_for_token)

            tree_item.setExpanded(True)
            tree_item = item_for_token

    def _get_selected_paths(self, item):
        result = []
        if item.childCount()>0:
            # Intermdeiate nodes
            for i in range(item.childCount()):
                result += self._get_selected_paths(item.child(i))
        else:
            # Leaf nodes
            if item.checkState(0)==qt.Checked:
                result += [item.data(0, USER_ROLE_PATH)]
        return result

    def selected_paths(self):
        return self._get_selected_paths(self.invisibleRootItem())

    def contextMenuEvent(self, event):
        menu = widgets.QMenu()
        select_all = menu.addAction("Select All")
        select_none = menu.addAction("Select None")
        menu.addSeparator()
        select_by_expression = menu.addAction("Select by Expression")
        result = menu.exec_(event.globalPos())

        if result==select_all:
            self.walk(self.invisibleRootItem(), lambda item : item.setCheckState(0, qt.Checked))
        elif result==select_none:
            self.walk(self.invisibleRootItem(), lambda item : item.setCheckState(0, qt.Unchecked))
        elif result==select_by_expression:
            expression, result = widgets.QInputDialog.getText(None, "Select USD Mesh by Expression", "Type the expression")
            if result:
                # Check validity and sort checking and unchecking
                paths = map(lambda x: x.strip(), expression.split(","))
                check_paths = []
                uncheck_paths = []
                invalid_paths = []
                for path in paths:
                    path = path.strip()
                    if path.startswith("!"):
                        if self.is_path_valid(path[1:]):
                            uncheck_paths.append(path[1:].strip())
                        else:
                            invalid_paths.append(path)
                    else:
                        if self.is_path_valid(path):
                            check_paths.append(path)
                        else:
                            invalid_paths.append(path)

                if len(invalid_paths)>0:
                    mari.utils.message("Invalid paths were found. There are no prims specified by these paths.", "Invalid Expression", icon=widgets.QMessageBox.Warning, details="\n".join(invalid_paths))
                else:
                    # First select none
                    self.walk(self.invisibleRootItem(), lambda item : item.setCheckState(0, qt.Unchecked))

                    for path in check_paths:
                        self.visit(self.invisibleRootItem(), list(filter(None, path.split("/"))), None, lambda item : item.setCheckState(0, qt.Checked))
                    for path in uncheck_paths:
                        # Apply uncheck after all checking for negation to take priority
                        self.visit(self.invisibleRootItem(), list(filter(None, path.split("/"))), None, lambda item : item.setCheckState(0, qt.Unchecked))

    def walk(self, item, func):
        for i in range(item.childCount()):
            self.walk(item.child(i), func)
        func(item)

    def visit(self, item, path_tokens, func, leaf_func):
        if len(path_tokens)==0:
            if leaf_func:
                leaf_func(item)
            return
        child_path_token = path_tokens.pop(0)
        # Visit only the child matching the path token.
        for i in range(item.childCount()):
            child = item.child(i)
            if child.text(0)==child_path_token:
                self.visit(child, path_tokens, func, leaf_func)
        if func:
            func(item)

    def is_path_valid(self, path):
        return path in self._item_map


class UsdLoaderWidget(widgets.QWidget):
    def __init__(self, parent = None):
        widgets.QWidget.__init__(self, parent = parent)

        layout = widgets.QFormLayout()
        layout.setSpacing(10)
        self.setLayout(layout)

        self._selection_dirty = False
        self._selection_update_timer = core.QTimer()
        self._selection_update_timer.setInterval(200)
        self._selection_update_timer.timeout.connect(self._selection_update)

        self.tree_widget = UsdLoaderTreeWidget()
        self.tree_widget.setMinimumHeight(300)
        layout.addRow(self.tree_widget)

        self.tree_widget.itemChanged.connect(self._request_selection_update)

        self.selected_items_edit = widgets.QLineEdit()
        self.selected_items_edit.setReadOnly(True)
        self.selected_items_edit.setToolTip('''Displays the list of meshes selected in the tree''')
        layout.addRow("Selected Items", self.selected_items_edit)

        self.merge_type_box = widgets.QComboBox()
        self.merge_type_box.setToolTip("""Specify whether to merge the models in the file into a single Object
  - Merge Models : Merge the models into a single Object
  - Keep Models Separate : Keep the models separate""")
        layout.addRow("Merge Type",self.merge_type_box)

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

        # Update the tree widget
        mesh_path = mari.app.currentMeshPathInGeoLoader()
        root_layer = Sdf.Layer.FindOrOpen(mesh_path)
        stage = Usd.Stage.Open(root_layer)
        self.tree_widget.populate(stage)

        self._request_selection_update()

    def hideEvent(self, event):
        mari.app.setGeoPluginAttribute("Merge Type", self.merge_type_box.currentText())
        mari.app.setGeoPluginAttribute("UV Set", self.uv_set_box.currentText())
        mari.app.setGeoPluginAttribute("Mapping Scheme", self.mapping_scheme_box.currentText())
        mari.app.setGeoPluginAttribute("Frame Numbers", self.frame_numbers_edit.text())
        mari.app.setGeoPluginAttribute("Variants", self.variants_edit.text())
        mari.app.setGeoPluginAttribute("Keep Centered", self.keep_centered_checkbox.checkState() == qt.Checked)
        mari.app.setGeoPluginAttribute("Conform to Mari Y as up", self.conform_y_up_checkbox.checkState() == qt.Checked)
        mari.app.setGeoPluginAttribute("Include Invisible", self.include_invisible_checkbox.checkState() == qt.Checked)
        mari.app.setGeoPluginAttribute("Create Face Selection Group per mesh", self.create_face_selection_group_checkbox.checkState() == qt.Checked)

        # Fill model names based on the tree view
        mari.app.setGeoPluginAttribute("Load", "Specified Models in Model Names")
        mari.app.setGeoPluginAttribute("Model Names", ",".join(self.tree_widget.selected_paths()))

    def _request_selection_update(self):
        self._selection_dirty = True
        self._selection_update_timer.start()

    def _selection_update(self):
        self._selection_dirty = False
        self._selection_update_timer.stop()

        self.selected_items_edit.setText(",".join(self.tree_widget.selected_paths()))

usd_loader_widget = UsdLoaderWidget()
if mari.app.isRunning():
    mari.app.registerGeoPluginWidget(["usda", "usdc", "usdz", "usd"], usd_loader_widget)

