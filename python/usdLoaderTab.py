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
import importlib
from fnpxr import Sdf, Usd, UsdGeom

for base_module in ['PySide6', 'PySide2']:  # Dual Qt6/Qt5 support.
    try:
        core = importlib.import_module(f'{base_module}.QtCore')
        gui = importlib.import_module(f'{base_module}.QtGui')
        widgets = importlib.import_module(f'{base_module}.QtWidgets')
        break
    except (ImportError, ModuleNotFoundError):
        continue
else:
    raise ImportError("Neither PySide6 nor PySide2 is available")

USER_ROLE_PATH = core.Qt.UserRole

# Column indices for tree widget
COLUMN_PATH = 0
COLUMN_TYPE = 1
COLUMN_VARIANT_SETS = 2

CONFORM_TO_MARI_Y_AS_UP_ICON = mari.resources.createIcon("USDImporterIcons_ConformToMariYasUp.svg")
CREATE_FACE_SELECTION_GROUP_PER_MESH_ICON = (
    mari.resources.createIcon("USDImporterIcons_CreateFaceSelectionGroupPerMesh.svg")
)
INCLUDE_INVISIBLE_ICON = mari.resources.createIcon("USDImporterIcons_IncludeInvisible.svg")
KEEP_CENTERED_ICON = mari.resources.createIcon("USDImporterIcons_KeepCentered.svg")
SELECT_ALL_ICON = mari.resources.createIcon("SelectAll.png")
SELECT_NONE_ICON = mari.resources.createIcon("SelectNone.png")
SELECT_BY_EXPRESSION_ICON = mari.resources.createIcon("SelectByExpression.svg")
EXPAND_ALL_ICON = mari.resources.createIcon("ExpandAll.svg")
COLLAPSE_ALL_ICON = mari.resources.createIcon("CollapseAll.svg")
SHOW_SELECTED_ONLY_ICON = mari.resources.createIcon("SelectVisible.png")


class UsdLoaderTreeWidget(widgets.QTreeWidget):

    def __init__(self, Parent=None):
        widgets.QTreeWidget.__init__(self, Parent)

        self.setColumnCount(3)
        self.headerItem().setText(COLUMN_PATH, "Path")
        self.headerItem().setText(COLUMN_TYPE, "Type")
        self.headerItem().setText(COLUMN_VARIANT_SETS, "Variant Sets")

        self.header().setSectionResizeMode(widgets.QHeaderView.Stretch)
        self.header().setStretchLastSection(False)

        self.stage = None

    def populate(self, stage):
        self.clear()
        self._item_map = {}
        self.stage = stage
        for prim in stage.TraverseAll():
            self._create_tree_node(prim, stage)

        self._expand_to_level(self.invisibleRootItem(), 0, 2)

    def _expand_to_level(self, item, level, target):
        if level <= target or target < 0:
            item.setExpanded(True)
        else:
            item.setExpanded(False)
        for i in range(item.childCount()):
            self._expand_to_level(item.child(i), level+1, target)

    def _is_prim_supported(self, prim: Usd.Prim) -> bool:
        if not prim.IsValid():
            return False

        # Mesh is always supported (mandatory)
        if prim.IsA(UsdGeom.Mesh):
            return True

        # Cameras are always shown, but remain unchecked by default
        if prim.IsA(UsdGeom.Camera):
            return True

        return False

    def _should_auto_check(self, prim: Usd.Prim) -> bool:
        if not prim.IsValid():
            return False

        if prim.IsA(UsdGeom.Mesh):
            return True

        return False

    def _create_tree_node(self, prim, stage):
        if not self._is_prim_supported(prim):
            # Support loading only a subset of Usd prim types
            return
        prim_path = str(prim.GetPath())
        tree_item = self.invisibleRootItem()
        for token in str(prim_path[1:]).split("/"):
            item_for_token = None
            for i in range(tree_item.childCount()):
                child_item = tree_item.child(i)
                if child_item.text(COLUMN_PATH) == token:
                    item_for_token = child_item
            if item_for_token is None:
                item_for_token = widgets.QTreeWidgetItem()
                path = tree_item.data(COLUMN_PATH, USER_ROLE_PATH)
                path = "/"+token if path is None else path+"/"+token
                self._item_map[path] = item_for_token
                item_for_token.setData(COLUMN_PATH, USER_ROLE_PATH, path)

                # Determine initial check state based on prim type
                prim_for_token = stage.GetPrimAtPath(path)
                should_check = self._should_auto_check(prim_for_token) if prim_for_token.IsValid() else False

                # Set flags - make checkable and enable auto-tristate for proper parent state updates
                item_for_token.setFlags(
                    item_for_token.flags() | core.Qt.ItemIsUserCheckable | core.Qt.ItemIsAutoTristate
                )

                item_for_token.setCheckState(COLUMN_PATH, core.Qt.Checked if should_check else core.Qt.Unchecked)

                item_for_token.setText(COLUMN_PATH, token)
                tree_item.addChild(item_for_token)

                # Set the prim type in column 1
                if prim_for_token.IsValid():
                    prim_type = prim_for_token.GetTypeName()
                    item_for_token.setText(COLUMN_TYPE, str(prim_type) if prim_type else "")

                # Handle variant sets in column 2
                if prim_for_token.HasVariantSets():
                    variant_sets_widget = widgets.QWidget()
                    variant_sets_layout = widgets.QFormLayout()
                    variant_sets_layout.setContentsMargins(1, 1, 1, 1)
                    variant_sets_widget.setLayout(variant_sets_layout)
                    for variant_set_name in prim_for_token.GetVariantSets().GetNames():
                        variant_set = prim_for_token.GetVariantSet(variant_set_name)
                        combobox = widgets.QComboBox()
                        combobox.addItems(variant_set.GetVariantNames())
                        combobox.setCurrentText(variant_set.GetVariantSelection())
                        variant_sets_layout.addRow(variant_set_name, combobox)
                        combobox.setProperty("prim_path", path)
                        combobox.setProperty("variant_set_name", variant_set_name)
                        combobox.currentIndexChanged.connect(self.onVariantComboboxCurrentIndexChanged)
                    self.setItemWidget(item_for_token, COLUMN_VARIANT_SETS, variant_sets_widget)

            tree_item = item_for_token

    def onVariantComboboxCurrentIndexChanged(self, index):
        if self.stage is None:
            return
        combobox = self.sender()
        path = combobox.property("prim_path")
        prim = self.stage.GetPrimAtPath(path)
        variant_set_name = combobox.property("variant_set_name")
        variant_set = prim.GetVariantSet(variant_set_name)
        variant_set.SetVariantSelection(combobox.currentText())

        self.populate(self.stage)

    def _get_selected_leaf_paths(self, item):
        result = []
        if item.childCount() > 0:
            # Intermediate nodes
            for i in range(item.childCount()):
                result += self._get_selected_leaf_paths(item.child(i))
        else:
            # Leaf nodes
            if item.checkState(COLUMN_PATH) == core.Qt.Checked:
                result += [item.data(COLUMN_PATH, USER_ROLE_PATH)]
        return result

    def selected_leaf_paths(self):
        return self._get_selected_leaf_paths(self.invisibleRootItem())

    def _get_selected_paths(self, item):
        if item.checkState(COLUMN_PATH) == core.Qt.Checked:
            # Total selection. Stop here returning the path to here.
            return [item.data(COLUMN_PATH, USER_ROLE_PATH)]
        elif item.checkState(COLUMN_PATH) == core.Qt.Unchecked:
            # No selection. Stop here returning nothing.
            return []
        else:
            # Partial selection. Dig in deeper and find out what's selected.
            result = []
            for i in range(item.childCount()):
                result += self._get_selected_paths(item.child(i))
            return result

    def selected_paths(self):
        result = []
        root_item = self.invisibleRootItem()
        for i in range(root_item.childCount()):
            result += self._get_selected_paths(root_item.child(i))
        return result

    def _get_selected_variants(self, item):
        if item.checkState(COLUMN_PATH) == core.Qt.Unchecked:
            # No selection. Stop here returning nothing.
            return []

        # Get the variant info
        result = []
        widget = self.itemWidget(item, COLUMN_VARIANT_SETS)
        if widget:
            path = item.data(COLUMN_PATH, USER_ROLE_PATH)
            layout = widget.layout()
            for row in range(layout.rowCount()):
                label = layout.itemAt(row, widgets.QFormLayout.LabelRole).widget()
                combobox = layout.itemAt(row, widgets.QFormLayout.FieldRole).widget()
                path_with_variant = path+"{"+label.text()+"="+combobox.currentText()+"}"
                result.append(path_with_variant)

        # Total/Partial selection. Dig in deeper and find out what's selected.
        for i in range(item.childCount()):
            result += self._get_selected_variants(item.child(i))
        return result

    def selected_variants(self):
        result = []
        root_item = self.invisibleRootItem()
        for i in range(root_item.childCount()):
            result += self._get_selected_variants(root_item.child(i))
        return result

    def walk(self, item, func):
        for i in range(item.childCount()):
            self.walk(item.child(i), func)
        func(item)

    def visit(self, item, path_tokens, func, leaf_func):
        if len(path_tokens) == 0:
            if leaf_func:
                leaf_func(item)
            return
        child_path_token = path_tokens.pop(0)
        # Visit only the child matching the path token.
        for i in range(item.childCount()):
            child = item.child(i)
            if child.text(COLUMN_PATH) == child_path_token:
                self.visit(child, path_tokens, func, leaf_func)
        if func:
            func(item)

    def is_path_valid(self, path):
        return path in self._item_map


class UsdLoaderWidget(widgets.QWidget):
    def __init__(self, parent=None):
        widgets.QWidget.__init__(self, parent=parent)

        layout = widgets.QFormLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Add tree control buttons
        filter_layout = widgets.QHBoxLayout()
        filter_layout.addStretch(1)

        # Add tree control buttons on the right side
        self.select_all_button = widgets.QPushButton(SELECT_ALL_ICON, "")
        self.select_all_button.setToolTip("Select all items in the tree")
        self.select_all_button.clicked.connect(self._on_select_all)
        filter_layout.addWidget(self.select_all_button)

        self.select_none_button = widgets.QPushButton(SELECT_NONE_ICON, "")
        self.select_none_button.setToolTip("Deselect all items in the tree")
        self.select_none_button.clicked.connect(self._on_select_none)
        filter_layout.addWidget(self.select_none_button)

        self.select_by_expression_button = widgets.QPushButton(SELECT_BY_EXPRESSION_ICON, "")
        self.select_by_expression_button.setToolTip("Select items using a path expression")
        self.select_by_expression_button.clicked.connect(self._on_select_by_expression)
        filter_layout.addWidget(self.select_by_expression_button)

        self.show_selected_only_button = widgets.QPushButton(SHOW_SELECTED_ONLY_ICON, "")
        self.show_selected_only_button.setToolTip("Show selected items in a separate view")
        self.show_selected_only_button.clicked.connect(self._on_show_selected_only)
        filter_layout.addWidget(self.show_selected_only_button)

        self.expand_all_button = widgets.QPushButton(EXPAND_ALL_ICON, "")
        self.expand_all_button.setToolTip("Expand all tree nodes")
        self.expand_all_button.clicked.connect(self._on_expand_all)
        filter_layout.addWidget(self.expand_all_button)

        self.collapse_all_button = widgets.QPushButton(COLLAPSE_ALL_ICON, "")
        self.collapse_all_button.setToolTip("Collapse all tree nodes")
        self.collapse_all_button.clicked.connect(self._on_collapse_all)
        filter_layout.addWidget(self.collapse_all_button)

        layout.addRow(filter_layout)

        self.tree_widget = UsdLoaderTreeWidget()
        self.tree_widget.setMinimumHeight(200)
        layout.addRow(self.tree_widget)

        options = widgets.QGroupBox("Options")
        layout.addRow(options)

        options_layout = widgets.QGridLayout()
        options.setLayout(options_layout)
        options_layout.setColumnStretch(0, 0)
        options_layout.setColumnStretch(1, 1)
        options_layout.setColumnStretch(2, 0)
        options_layout.setColumnStretch(3, 1)

        self.merge_type_box = widgets.QComboBox()
        self.merge_type_box.setToolTip("""Specify whether to merge the models in the file into a single Object
  - Merge Models : Merge the models into a single Object
  - Keep Models Separate : Keep the models separate""")
        options_layout.addWidget(widgets.QLabel("Merge Type"), 0, 0)
        options_layout.addWidget(self.merge_type_box, 0, 1)

        self.uv_set_box = widgets.QComboBox()
        self.uv_set_box.setToolTip("""Specify the UV set to load""")
        options_layout.addWidget(widgets.QLabel("UV Set"), 0, 2)
        options_layout.addWidget(self.uv_set_box, 0, 3)

        self.frame_numbers_edit = widgets.QLineEdit()
        self.frame_numbers_edit.setToolTip("""Specify the frame numbers to load""")
        self.frame_numbers_edit.setText("1")
        options_layout.addWidget(widgets.QLabel("Frame Numbers"), 1, 0)
        options_layout.addWidget(self.frame_numbers_edit, 1, 1)

        self.mapping_scheme_box = widgets.QComboBox()
        self.mapping_scheme_box.setToolTip("""Specify the mode for UV layout
  - UV if available, Ptex otherwise : Load the UV layout if available. If there is no UV layout, Ptex texture is created
  - Force Ptex : Force to create Ptex texture no matter if there is UV layout
  - UV if available, empty otherwise : Load the UV layout if available. If there is no UV layout, an empty UV layout
  - Force empty : Force to create empty UV layout no matter if there is UV layout""")
        options_layout.addWidget(widgets.QLabel("Mapping Scheme"), 1, 2)
        options_layout.addWidget(self.mapping_scheme_box, 1, 3)

        checkbox_layout = widgets.QHBoxLayout()
        checkbox_layout.addStretch(1)

        self.keep_centered_checkbox = widgets.QPushButton(KEEP_CENTERED_ICON, "")
        self.keep_centered_checkbox.setCheckable(True)
        self.keep_centered_checkbox.setToolTip("""Enable to discard model transforms and keep everything centered""")
        checkbox_layout.addWidget(self.keep_centered_checkbox)

        self.conform_y_up_checkbox = widgets.QPushButton(CONFORM_TO_MARI_Y_AS_UP_ICON, "")
        self.conform_y_up_checkbox.setCheckable(True)
        self.conform_y_up_checkbox.setToolTip("""Enable to alter the model orientation to conform to Mari's Y as up""")
        self.conform_y_up_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.conform_y_up_checkbox)

        self.include_invisible_checkbox = widgets.QPushButton(INCLUDE_INVISIBLE_ICON, "")
        self.include_invisible_checkbox.setCheckable(True)
        self.include_invisible_checkbox.setToolTip("""Enable to load invisible models""")
        checkbox_layout.addWidget(self.include_invisible_checkbox)

        self.create_face_selection_group_checkbox = widgets.QPushButton(CREATE_FACE_SELECTION_GROUP_PER_MESH_ICON, "")
        self.create_face_selection_group_checkbox.setCheckable(True)
        self.create_face_selection_group_checkbox.setToolTip("""Enable to create selection groups per mesh""")
        checkbox_layout.addWidget(self.create_face_selection_group_checkbox)

        options_layout.addLayout(checkbox_layout, 2, 0, 4, 0)

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

        # Force reload from disk by clearing any cached layer first
        existing_layer = Sdf.Layer.Find(mesh_path)
        if existing_layer:
            # If layer is already loaded, reload it to pick up any file changes
            existing_layer.Reload()
            root_layer = existing_layer
        else:
            # Layer not in cache, open it fresh
            root_layer = Sdf.Layer.FindOrOpen(mesh_path)

        # Open the stage with the (potentially reloaded) layer
        stage = Usd.Stage.Open(root_layer)
        self.tree_widget.populate(stage)

    def hideEvent(self, event):
        mari.app.setGeoPluginAttribute("Merge Type", self.merge_type_box.currentText())
        mari.app.setGeoPluginAttribute("UV Set", self.uv_set_box.currentText())
        mari.app.setGeoPluginAttribute("Mapping Scheme", self.mapping_scheme_box.currentText())
        mari.app.setGeoPluginAttribute("Frame Numbers", self.frame_numbers_edit.text())
        mari.app.setGeoPluginAttribute("Keep Centered", self.keep_centered_checkbox.isChecked())
        mari.app.setGeoPluginAttribute("Conform to Mari Y as up", self.conform_y_up_checkbox.isChecked())
        mari.app.setGeoPluginAttribute("Include Invisible", self.include_invisible_checkbox.isChecked())
        mari.app.setGeoPluginAttribute(
            "Create Face Selection Group per mesh",
            self.create_face_selection_group_checkbox.isChecked()
        )

        # Fill model names based on the tree view
        mari.app.setGeoPluginAttribute("Load", "Specified Models in Model Names")
        mari.app.setGeoPluginAttribute("Model Names", ",".join(self.tree_widget.selected_leaf_paths()))
        mari.app.setGeoPluginAttribute("Variants", " ".join(self.tree_widget.selected_variants()))

    def _on_select_all(self):
        """Select all items in the tree."""
        self.tree_widget.walk(
            self.tree_widget.invisibleRootItem(),
            lambda item: item.setCheckState(COLUMN_PATH, core.Qt.Checked)
        )

    def _on_select_none(self):
        """Deselect all items in the tree."""
        self.tree_widget.walk(
            self.tree_widget.invisibleRootItem(),
            lambda item: item.setCheckState(COLUMN_PATH, core.Qt.Unchecked)
        )

    def _on_select_by_expression(self):
        """Select items using a path expression."""
        dialog = widgets.QInputDialog()
        dialog.setWindowTitle("Select USD Mesh by Expression")
        dialog.setLabelText("Type the expression")
        dialog.setTextValue("")
        line_edit = dialog.children()[1]
        line_edit.setToolTip(
            'Enter a list of comma-delimited prim paths to be selected for loading. '
            'Use "!" to exclude prims from the list by prefixing the path with an exclamation mark "!"\n'
            ' e.g. "/root/group, !/root/group/sphere" will select all prims in /root/group except for sphere.'
        )
        if dialog.exec() == dialog.Accepted:
            # Check validity and sort checking and unchecking
            paths = dialog.textValue().split(",")
            check_paths = []
            uncheck_paths = []
            invalid_paths = []
            for path in paths:
                path = path.strip()
                if path.startswith("!"):
                    if self.tree_widget.is_path_valid(path[1:].strip()):
                        uncheck_paths.append(path[1:].strip())
                    else:
                        invalid_paths.append(path)
                else:
                    if self.tree_widget.is_path_valid(path):
                        check_paths.append(path)
                    else:
                        invalid_paths.append(path)

            if len(invalid_paths) > 0:
                mari.utils.message(
                    "Invalid paths were found. There are no prims specified by these paths.",
                    "Invalid Expression",
                    icon=widgets.QMessageBox.Warning,
                    details="\n".join(invalid_paths)
                )
            else:
                # First select none
                self.tree_widget.walk(
                    self.tree_widget.invisibleRootItem(),
                    lambda item: item.setCheckState(COLUMN_PATH, core.Qt.Unchecked)
                )

                for path in check_paths:
                    self.tree_widget.visit(
                        self.tree_widget.invisibleRootItem(),
                        list(filter(None, path.split("/"))),
                        None,
                        lambda item: item.setCheckState(COLUMN_PATH, core.Qt.Checked)
                    )
                for path in uncheck_paths:
                    # Apply uncheck after all checking for negation to take priority
                    self.tree_widget.visit(
                        self.tree_widget.invisibleRootItem(),
                        list(filter(None, path.split("/"))),
                        None,
                        lambda item: item.setCheckState(COLUMN_PATH, core.Qt.Unchecked)
                    )

    def _on_expand_all(self):
        """Expand all tree nodes."""
        self.tree_widget.expandAll()

    def _on_collapse_all(self):
        """Collapse all tree nodes."""
        self.tree_widget.collapseAll()

    def _on_show_selected_only(self):
        """Show selected items in a separate dialog."""
        dialog = widgets.QDialog(self)
        dialog.setWindowTitle("Selected Items")
        dialog.setMinimumSize(600, 400)

        layout = widgets.QVBoxLayout()
        dialog.setLayout(layout)

        # Create a read-only tree widget
        tree = widgets.QTreeWidget()
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Path", "Type"])
        tree.header().setSectionResizeMode(widgets.QHeaderView.Stretch)
        layout.addWidget(tree)

        # Populate with selected items only
        self._populate_selected_tree(tree.invisibleRootItem(), self.tree_widget.invisibleRootItem())
        tree.expandAll()

        # Add close button
        button_layout = widgets.QHBoxLayout()
        button_layout.addStretch()
        close_button = widgets.QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        dialog.exec()

    def _populate_selected_tree(self, dest_parent, src_parent):
        """Recursively copy only checked items to the destination tree."""
        for i in range(src_parent.childCount()):
            src_item = src_parent.child(i)
            check_state = src_item.checkState(COLUMN_PATH)

            # Include item if it's checked or partially checked (has checked descendants)
            if check_state == core.Qt.Checked or check_state == core.Qt.PartiallyChecked:
                dest_item = widgets.QTreeWidgetItem()
                dest_item.setText(0, src_item.text(COLUMN_PATH))
                dest_item.setText(1, src_item.text(COLUMN_TYPE))

                # Show check state indicator
                if check_state == core.Qt.Checked:
                    dest_item.setText(0, "✓ " + src_item.text(COLUMN_PATH))
                elif check_state == core.Qt.PartiallyChecked:
                    dest_item.setText(0, "▬ " + src_item.text(COLUMN_PATH))

                dest_parent.addChild(dest_item)

                # Recursively add children
                self._populate_selected_tree(dest_item, src_item)


usd_loader_widget = UsdLoaderWidget()
if mari.app.isRunning():
    mari.app.registerGeoPluginWidget(["usda", "usdc", "usdz", "usd"], usd_loader_widget)
