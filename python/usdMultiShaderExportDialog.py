# Copyright 2022 Foundry
#
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification you may not use this file except in
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
import PySide2.QtGui as gui
import PySide2.QtWidgets as widgets
from PySide2.QtCore import Qt as qt
from . import usdExportManagerTab, usdShadeExport
import json
import xml.etree.ElementTree as etree

# When unifying usdExportManagerTab to this usdMultiShaderExportDialog, these implementation should be moved over
FileBrowseWidget = usdExportManagerTab.FileBrowseWidget
load_usd_target_dir_paths = usdExportManagerTab.USDExportWidget.load_usd_target_dir_paths 
load_usd_look_file_paths = usdExportManagerTab.USDExportWidget.load_usd_look_file_paths 
load_usd_assembly_file_paths = usdExportManagerTab.USDExportWidget.load_usd_assembly_file_paths 
load_usd_payload_file_paths = usdExportManagerTab.USDExportWidget.load_usd_payload_file_paths 
load_text_value = usdExportManagerTab.USDExportWidget.load_text_value 

USD_MULTI_SHADER_WIDGET = None

SELECTION_GRAOUP_COLUMN = 0
MATERIAL_COLUMN = 1
SHADER_COLUMN = 2

SHADER_ERROR_PIXMAP = gui.QPixmap(mari.resources.path(mari.resources.ICONS) + '/ShaderError.svg')

def resolveSourceIndex(index):
    """Returns the index of the source model if the index belongs to a proxy model.

    Args:
        index (QModelIndex): Index to resolve

    Returns:
        QModelIndex: Either the same or source index
    """
    if isinstance(index.model(), core.QAbstractProxyModel):
        return index.model().mapToSource(index)
    return index

def getExportItems(shader):
    """Gets ExportItems for the shader. If necessary, this creates ExportItems. Furthermore, this updates the allowlist of ExportItems to display in the view.

    Args:
        shader (mari.Shader): Shader to get ExportItems for.
    """
    if not shader:
        return []

    shader_node = shader.shaderNode()
    shader_model = shader.shaderModel()

    geo_entity = mari.geo.current()

    input_list = usdExportManagerTab.ExportItem_Model.advancedInputList(shader)

    exportItems = []

    for _, shader_input, shader_model_input_name in input_list:
        for export_item in mari.exports.exportItemList(geo_entity):
            if export_item and export_item.sourceNode() == shader_input and export_item.hasMetadata("_HIDDEN") and export_item.metadata("_HIDDEN"):
                exportItems.append((export_item, shader_model_input_name))
                break
        else:
            export_item = mari.ExportItem()
            export_item.setSourceNode(shader_input)
            template = shader_node.name().replace(" ","_")+ "." + shader_model_input_name.replace(" ","_")+ ".$UDIM.png"
            if template.endswith(".png") and shader_input.depth() != mari.Image.DEPTH_BYTE:
                template = template[:-4]+".exr"
            export_item.setFileTemplate(template)
            export_item.setMetadata("_STREAM", shader_model_input_name)
            export_item.setMetadata("_HIDDEN", True)
            mari.exports.addExportItem(export_item, geo_entity)
            exportItems.append((export_item, shader_model_input_name))

    return exportItems

class Material_Item():
    def __init__(self, name):
        self._name = name
        self._checked = qt.Checked
        self._assignments = {}
        self._selectionGroups = []

    def to_dict(self):
        assignments = {}
        for key in self._assignments:
            assignments[key] = self._assignments[key].uuid()
        usd_material_data = {
            "_name": self._name,
            "_checked": True if self._checked == qt.Checked else False,
            "_assignments": assignments,
            "_selectionGroups": self._selectionGroups,
        }
        return usd_material_data

    @classmethod
    def from_dict(cls, usd_material_data):
        name = usd_material_data["_name"]
        material = cls(name)

        material._name = name 
        material._checked = qt.Checked if usd_material_data["_checked"] else qt.Unchecked 
        material._selectionGroups = usd_material_data["_selectionGroups"] 
        material._assignments = {}

        shader_map = {}
        for shader in mari.geo.current().shaderList():
            shader_map[shader.uuid()] = shader

        assignments = usd_material_data["_assignments"]
        for key in assignments:
            uuid = assignments[key]
            if uuid in shader_map:
                material._assignments[key] = shader_map[uuid]

        return material
            

class Material_View(widgets.QTableView):
    currentIndexChanged = core.Signal(core.QModelIndex)
    editShaderInputsTriggered = core.Signal()
    addNewMaterialTriggered = core.Signal()
    deleteMaterialTriggered = core.Signal()

    def __init__(self, parent = None):
        widgets.QTableView.__init__(self, parent = parent)

    def initialize(self):
        self.horizontalHeader().setSectionResizeMode(SELECTION_GRAOUP_COLUMN, widgets.QHeaderView.Fixed)
        self.resizeColumnsToContents()

    def currentChanged(self, current, previous):
        self.horizontalHeader().setSectionResizeMode(SELECTION_GRAOUP_COLUMN, widgets.QHeaderView.Fixed)
        result = super(Material_View, self).currentChanged(current, previous)
        self.currentIndexChanged.emit(current)
        return result

    def contextMenuEvent(self, event):
        menu = widgets.QMenu()
        edit_shader_inputs = menu.addAction("Edit Shader Inputs")
        edit_shader_inputs.triggered.connect(self.editShaderInputsTriggered)
        add_new_material = menu.addAction("Add New Material")
        add_new_material.triggered.connect(self.addNewMaterialTriggered)
        delete_material = menu.addAction("Delete Material")
        delete_material.triggered.connect(self.deleteMaterialTriggered)
        menu.exec_(self.mapToGlobal(event.pos()))
        return super(Material_View, self).contextMenuEvent(event)

class ShaderAssignment_Item_Delegate(widgets.QStyledItemDelegate):
    def __init__(self, parent = None):
        widgets.QStyledItemDelegate.__init__(self, parent = parent)

    def createEditor(self, parent, option, index):
        if index.column() >= SHADER_COLUMN:
            model = index.model()
            editor = widgets.QComboBox(parent)
            for shader_name, shader in model._shader_map[model._shader_model_list[index.column()-SHADER_COLUMN]]:
                editor.addItem(shader_name, shader)
            editor.currentIndexChanged.connect(self.finishEdit)

            return editor

        elif index.column() == MATERIAL_COLUMN:
            return widgets.QLineEdit(parent)

        return widgets.QStyledItemDelegate.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        if index.column() >= SHADER_COLUMN and isinstance(editor, widgets.QComboBox):
            model = index.model()
            shader_model_name = model._shader_model_list[index.column()-SHADER_COLUMN]
            assignments = model._material_list[index.row()]._assignments
            shader_name = ""
            if shader_model_name in assignments:
                shader_name = assignments[shader_model_name].name()
            editor.setCurrentText(shader_name)
            return
        elif index.column() == MATERIAL_COLUMN:
            material_name = index.model()._material_list[index.row()]._name
            editor.setText(material_name)
            return
        widgets.QStyledItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        if index.column() >= SHADER_COLUMN and isinstance(editor, widgets.QComboBox):
            shader_model_name = model._shader_model_list[index.column()-SHADER_COLUMN]
            model._material_list[index.row()]._assignments[shader_model_name] = editor.currentData()
            return
        elif index.column() == MATERIAL_COLUMN and isinstance(editor, widgets.QLineEdit):
            model._material_list[index.row()]._name = editor.text()
            return

        widgets.QStyledItemDelegate.setModelData(self, editor, model, index)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def finishEdit(self):
        editor = self.sender()
        if isinstance(editor, widgets.QComboBox):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, self.NoHint)
            return
        widgets.QStyledItemDelegate.finishEdit(self)



class Material_Model(core.QAbstractItemModel):
    def __init__(self, parent = None):
        core.QAbstractItemModel.__init__(self, parent = parent)

        self._shader_model_list = []
        self._shader_map = {}
        self._refreshShaders()

        self._material_list = []

        self._selection_group_icon = mari.resources.createIcon("SelectionSet.png")
        self._selection_group_history_icon = gui.QIcon(mari.resources.path(mari.resources.ICONS) + '/SelectionGroupsHistory.svg')
        self._shader_error_icon = gui.QIcon(SHADER_ERROR_PIXMAP)

    def headerData(self, section, orientation, role):
        if orientation == qt.Horizontal:
            if role == qt.DisplayRole:
                if section == SELECTION_GRAOUP_COLUMN:
                    return None 
                elif section == MATERIAL_COLUMN:
                    return "Material"
                elif section < len(self._shader_model_list)+SHADER_COLUMN:
                    return self._shader_model_list[section-2]
            elif role == qt.DecorationRole:
                if section == SELECTION_GRAOUP_COLUMN:
                    return self._selection_group_icon 
            elif role == qt.TextAlignmentRole:
                return qt.AlignHCenter
        return None

    def saveMaterials(self):
        if not mari.projects.current():
            return

        material_list = [material.to_dict() for material in self._material_list]

        json_data = json.dumps(material_list)

        mari.projects.current().setMetadata("_USDMultiShaderExport_Materials", json_data)

    def loadMaterials(self):
        if not mari.projects.current():
            return

        if mari.projects.current().hasMetadata("_USDMultiShaderExport_Materials"):
            self.layoutAboutToBeChanged.emit()

            self._material_list = []

            json_data = mari.projects.current().metadata("_USDMultiShaderExport_Materials")

            material_list = json.loads(json_data)

            for material_dict in material_list:
                material = Material_Item.from_dict(material_dict) 
                self._material_list.append(material)

            # Trigger redraw
            self.layoutChanged.emit()

    def addMaterial(self):
        existing_material_names = set([material._name for material in self._material_list])
        i=1
        material_name = ""
        while True:
            material_name = "Material"+str(i)
            if not material_name in existing_material_names:
                break
            i += 1

        self.layoutAboutToBeChanged.emit()

        material = Material_Item(material_name)
        self._material_list.append(material)

        # Trigger redraw
        self.layoutChanged.emit()

        self.saveMaterials()

    def removeMaterials(self, rows_to_remove):
        # Remove from reverse sorted list to remove correct items
        rows_to_remove.sort()
        rows_to_remove.reverse()

        for row in rows_to_remove:
            if row >= 0 and row < len(self._material_list):
                del self._material_list[row]

        # Trigger redraw
        self.layoutChanged.emit()

        self.saveMaterials()

    def _refreshShaders(self):
        self._shader_model_list = []
        self._shader_map = {}

        if not mari.geo.current():
            return

        for shader in mari.geo.current().shaderList():
            shader_model = shader.shaderModel()
            if not shader_model:
                continue
            shader_model_name = shader_model.id()
            if not shader_model_name in self._shader_map:
                self._shader_map[shader_model_name] = [("", None)]
            self._shader_map[shader_model_name].append((shader.name(), shader))
        for shader_names in self._shader_map.values():
            shader_names.sort(key=lambda x:x[0])
        self._shader_model_list = list(self._shader_map.keys())
        self._shader_model_list.sort()

    def data(self, index, role):
        if role == qt.DisplayRole:
            row = index.row()
            col = index.column()
            material = self._material_list[row] 
            if col == MATERIAL_COLUMN:
                return material._name
            elif col == SELECTION_GRAOUP_COLUMN:
                return None
            else:
                shader_model_name = self._shader_model_list[index.column()-SHADER_COLUMN]
                assignments = self._material_list[row]._assignments
                if shader_model_name in assignments and assignments[shader_model_name] != None:
                    return assignments[shader_model_name].name()
                else:
                    return ""
        elif role == qt.DecorationRole:
            row = index.row()
            col = index.column()
            if col == SELECTION_GRAOUP_COLUMN:
                return self._selection_group_history_icon if self._material_list[row]._selectionGroups else None 
            if col >= SHADER_COLUMN:
                shader_model_name = self._shader_model_list[index.column()-SHADER_COLUMN]
                assignments = self._material_list[row]._assignments
                if shader_model_name in assignments and assignments[shader_model_name] != None:
                    shader = assignments[shader_model_name]
                    input_list = usdExportManagerTab.ExportItem_Model.advancedInputList(shader)
                    if not input_list:
                        return self._shader_error_icon
        elif role == qt.CheckStateRole and index.column()==MATERIAL_COLUMN:
            material = self._material_list[index.row()] 
            return material._checked
        elif role == qt.ForegroundRole:
            if self._material_list[index.row()]._checked == qt.Unchecked:
                palette = gui.QPalette()
                return palette.brush(palette.Disabled, palette.Foreground)
        return None

    def setData(self, index, value, role):
        if role == qt.CheckStateRole and index.column()==MATERIAL_COLUMN:
            material = self._material_list[index.row()] 
            material._checked = value
            self.dataChanged.emit(index, index, [role])
            self.dataChanged.emit(index, self.createIndex(index.row(), self.columnCount()-1), [qt.ForegroundRole])
            return True
        return super(Material_Model, self).setData(index, value, role)

    def index(self, row, column, parent=core.QModelIndex()):
        return self.createIndex(row, column)

    def flags(self, index):
        default_flags = super(Material_Model, self).flags(index)
        if index.column() == MATERIAL_COLUMN:
            return default_flags | qt.ItemIsEditable | qt.ItemIsUserCheckable
        elif index.column() >= SHADER_COLUMN:
            return default_flags | qt.ItemIsEditable
        return default_flags

    def parent(self, index):
        return core.QModelIndex()

    def rowCount(self, parent=core.QModelIndex()):
        return len(self._material_list)

    def columnCount(self, parent=core.QModelIndex()):
        return len(self._shader_model_list) + SHADER_COLUMN

class ExportItemModel(mari.system.batch_export_dialog.ExportItemModel):
    def __init__(self, geoEntities, view):
        super(ExportItemModel, self).__init__(geoEntities, view)

    def data(self, index, role):
        index = resolveSourceIndex(index)
        if role == qt.DisplayRole and index.column()==0:
            # Shown stream names instead of channel/node names
            item = index.internalPointer()
            if isinstance(item, mari.ExportItem):
                if item.hasMetadata("_STREAM"):
                    return item.metadata("_STREAM")
        elif role == qt.DecorationRole:
            return None
        return super(ExportItemModel, self).data(index, role)


class ExportItemFilterModel(core.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(ExportItemFilterModel, self).__init__(parent)
        self.export_items = set()
        self._hide_unchecked = False

    def setExportItems(self, export_items):
        self.export_items = export_items

    def setHideUnchecked(self, hide):
        self._hide_unchecked = hide
        self.invalidate()

    def filterAcceptsRow(self, sourceRow, sourceParent):
        index = self.sourceModel().index(sourceRow, 0, sourceParent)

        item = index.internalPointer()
        if isinstance(item,mari.GeoEntity):
            return True

        # Hide the items not in the allowlist
        if not item in self.export_items:
            return False

        # Hide the item if the hide button is checked and the item is unchecked
        if self._hide_unchecked and not item.exportEnabled():
            return False

        return True

class MultiShaderExportWidget(widgets.QWidget):
    def __init__(self, parent = None):
        widgets.QWidget.__init__(self, parent)

        main_layout = widgets.QVBoxLayout()
        self.setLayout(main_layout)

        self.exportItems = set()

        self.model = Material_Model()

        button_layout = widgets.QHBoxLayout() 
        main_layout.addLayout(button_layout)

        middle_layout = widgets.QHBoxLayout()
        main_layout.addLayout(middle_layout)

        # Buttons
        add_material_button = widgets.QPushButton(mari.resources.createIcon("AddMaterial.svg"), "", self)
        add_material_button.pressed.connect(self.model.addMaterial)
        button_layout.addWidget(add_material_button)

        remove_material_button = widgets.QPushButton(mari.resources.createIcon("DeleteMaterial.svg"), "", self)
        remove_material_button.pressed.connect(self.removeSelectedMaterials)
        button_layout.addWidget(remove_material_button)

        button_layout.addSpacerItem(widgets.QSpacerItem(0, 0, widgets.QSizePolicy.MinimumExpanding))

        # Table
        self.view = Material_View(self)
        self.view.setModel(self.model)
        self.view.horizontalHeader().setSectionResizeMode(widgets.QHeaderView.Stretch)
        self.view.setSelectionBehavior(self.view.SelectRows)
        self.view.setSelectionMode(self.view.ExtendedSelection)
        self.view.setItemDelegate(ShaderAssignment_Item_Delegate(parent=self))
        self.view.initialize()
        middle_layout.addWidget(self.view, 3)

        # Selection Groups
        selection_group_layout = widgets.QVBoxLayout()
        middle_layout.addLayout(selection_group_layout, 1)
        selection_group_label_layout = widgets.QHBoxLayout()
        selection_group_layout.addLayout(selection_group_label_layout)

        selection_group_label = widgets.QLabel("Assigned Selection Groups", self)
        selection_group_label_layout.addWidget(selection_group_label, 1)

        adopt_selection_group_button = widgets.QPushButton(mari.resources.createIcon("Assign_SelectionGroup.svg"), "", self)
        adopt_selection_group_button.pressed.connect(self.assignSelectionGroups)
        selection_group_label_layout.addWidget(adopt_selection_group_button)

        self.selection_group_widget = widgets.QListWidget(self)
        selection_group_layout.addWidget(self.selection_group_widget)

        # Export Options
        options_group_box = widgets.QGroupBox("Export Options", self)
        main_layout.addWidget(options_group_box)
        options_layout = widgets.QGridLayout(options_group_box)
        options_layout.setHorizontalSpacing(5)
        options_layout.setVerticalSpacing(15)
        for index, stretch in enumerate((10, 20, 10, 20)):
            options_layout.setColumnStretch(index, stretch)

        self.export_usd_target_dir_widget = FileBrowseWidget(self, widgets.QFileDialog.Directory, "", load_usd_target_dir_paths())
        target_dir_label = widgets.QLabel("Texture Target Directory", self)
        target_dir_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(target_dir_label, 0, 0)
        options_layout.addWidget(self.export_usd_target_dir_widget, 0, 1)
        
        look_file_filter = "USD Look File (*.usd *.usda *.usdz)"
        self.look_file_widget = FileBrowseWidget(self, widgets.QFileDialog.AnyFile, look_file_filter, load_usd_look_file_paths())
        look_file_label = widgets.QLabel("USD Look File", self)
        look_file_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(look_file_label, 1, 0)
        options_layout.addWidget(self.look_file_widget, 1, 1)

        assembly_file_filter = "USD Assembly File (*.usd *.usda *.usdz)"
        self.assembly_file_widget = FileBrowseWidget(self, widgets.QFileDialog.AnyFile, assembly_file_filter, load_usd_assembly_file_paths())
        assembly_file_label= widgets.QLabel("USD Assembly File", self)
        assembly_file_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(assembly_file_label, 2, 0)
        options_layout.addWidget(self.assembly_file_widget, 2, 1)
        
        payload_file_filter = "USD (*.usd *.usda *.usdz)"
        self.payload_file_widget = FileBrowseWidget(self, widgets.QFileDialog.ExistingFile, payload_file_filter, load_usd_payload_file_paths())
        payload_label = widgets.QLabel("USD Payload", self)
        payload_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(payload_label, 3, 0)
        options_layout.addWidget(self.payload_file_widget, 3, 1)

        self.default_depth_combo_box = widgets.QComboBox(self)
        self.default_depth_combo_box.setSizePolicy(widgets.QSizePolicy.Expanding, widgets.QSizePolicy.Fixed)
        self.default_depth_combo_box.addItem("No Overrides", None)
        self.default_depth_combo_box.setToolTip("Overrides the bit depth of exported export items.\nWill not change export item until Export is triggered, will not change export items which are not exported.")
        for depth in mari.exports.depthList():
            self.default_depth_combo_box.addItem(depth, depth)
        override_depth_label = widgets.QLabel("Override Depth", self)
        override_depth_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(override_depth_label, 0, 2)
        options_layout.addWidget(self.default_depth_combo_box, 0, 3)

        self.default_size_combo_box = widgets.QComboBox(self)
        self.default_size_combo_box.setSizePolicy(widgets.QSizePolicy.Expanding, widgets.QSizePolicy.Fixed)
        self.default_size_combo_box.addItem("No Overrides", None)
        self.default_size_combo_box.setToolTip("Overrides the resolution of exported export items.\nWill not change export item until Export is triggered, will not change export items which are not exported.")
        for size in mari.exports.resolutionList():
            self.default_size_combo_box.addItem(size, size)
        override_resolution_label = widgets.QLabel("Override Resolution", self)
        override_resolution_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(override_resolution_label, 1, 2)
        options_layout.addWidget(self.default_size_combo_box, 1, 3)

        self.root_name_widget = widgets.QLineEdit(self)
        self.root_name_widget.setText(load_text_value("UsdRootName", "/root"))
        root_name_label = widgets.QLabel("Root Name", self)
        root_name_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(root_name_label, 2, 2)
        options_layout.addWidget(self.root_name_widget, 2, 3)

        self.uv_set_name_widget = widgets.QLineEdit(self)
        self.uv_set_name_widget.setText(load_text_value("UsdUvSetName", "st"))
        uv_set_name_label = widgets.QLabel("UV Set Name", self)
        uv_set_name_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(uv_set_name_label, 3, 2)
        options_layout.addWidget(self.uv_set_name_widget, 3, 3)


        # Export Button
        export_button = widgets.QPushButton(mari.resources.createIcon("ExportFile.svg"), "Export", self)
        export_button.pressed.connect(self.exportUsd)
        main_layout.addWidget(export_button)

        self.view.currentIndexChanged.connect(self.updateSelectionGroups)
        self.view.editShaderInputsTriggered.connect(self.editShaderInputs)
        self.view.addNewMaterialTriggered.connect(self.model.addMaterial)
        self.view.deleteMaterialTriggered.connect(self.removeSelectedMaterials)

        self.model.loadMaterials()

    def closeEvent(self, event):
        self.model.saveMaterials()
        event.accept()

    def removeSelectedMaterials(self):
        rows_to_remove = []
        for index in self.view.selectionModel().selectedRows():
            rows_to_remove.append(index.row())

        self.model.removeMaterials(rows_to_remove)

        self.updateSelectionGroups()

    def exportRootPath(self):
        return self.export_usd_target_dir_widget.path()

    def currentMaterial(self):
        current_index = self.view.currentIndex()
        row = current_index.row()
        if row >= 0 and row < len(self.model._material_list):
            return self.model._material_list[row]
        return None

    def assignSelectionGroups(self):
        material = self.currentMaterial()
        if not material:
            return
        material._selectionGroups = ["AAA", "BBB", "CCC"]
        self.updateSelectionGroups()
        self.emitDataChangedForCurrentRow(SELECTION_GRAOUP_COLUMN, [qt.DecorationRole])

    def emitDataChangedForCurrentRow(self, column, roles):
        index = self.view.currentIndex()
        index = self.model.createIndex(index.row(), column)
        self.model.dataChanged.emit(index, index, roles)

    def updateSelectionGroups(self):
        material = self.currentMaterial()
        if not material:
            return
        self.selection_group_widget.clear()
        self.selection_group_widget.addItems(material._selectionGroups)

    def exportUsd(self):
        usd_export_parameters = usdShadeExport.UsdExportParameters()
        usd_export_parameters.setExportRootPath(self.export_usd_target_dir_widget.path())
        usd_export_parameters.setLookfileTargetFilename(self.look_file_widget.path())
        usd_export_parameters.setAssemblyTargetFilename(self.assembly_file_widget.path())
        usd_export_parameters.setPayloadSourcePath(self.payload_file_widget.path())
        usd_export_parameters.setStageRootPath(self.root_name_widget.text())
        usd_export_parameters.setExportOverrides({"RESOLUTION":self.default_size_combo_box.currentText(), "DEPTH":self.default_depth_combo_box.currentText()})

        usd_material_sources = []
        for material in self.model._material_list:
            if not material._checked:
                continue

            for shader_model_name in material._assignments:
                shader = material._assignments[shader_model_name]
                if not shader:
                    continue

                node = shader.shaderNode()
                if not node:
                    continue

                node_graph = node.parentNodeGraph()
                if not node_graph:
                    continue

                geo_entity = node_graph.parentGeoEntity()
                if not geo_entity:
                    continue

                current_geo_version = geo_entity.currentVersion()
                if not current_geo_version:
                    continue

                usd_material_source = usdShadeExport.UsdMaterialSource(material._name)
                usd_material_source.setBindingLocations(current_geo_version.sourceMeshLocationList())
                usd_shader_source = usdShadeExport.UsdShaderSource(shader)
                usd_shader_source.setUvSetName("st")
                for export_item, shader_input_name in getExportItems(shader):
                    usd_shader_source.setInputExportItem(shader_input_name, export_item)
                usd_material_source.setShaderSource(shader.shaderModel().id(), usd_shader_source)
                usd_material_sources.append(usd_material_source)

        usdShadeExport.exportUsdShadeLook(usd_export_parameters, usd_material_sources)

    def editShaderInputs(self):
        index = self.view.currentIndex()
        shader_model_name = self.model._shader_model_list[index.column()-SHADER_COLUMN]
        assignments = self.model._material_list[index.row()]._assignments
        current_shader = None 
        if shader_model_name in assignments:
            current_shader = assignments[shader_model_name]

        shader_list = []
        for shader_name, shader in self.model._shader_map[shader_model_name]:
            shader_list.append((shader_name, shader))

        dialog = EditShaderInputsDialog(shader_model_name, current_shader, shader_list, self.getOverrides())

        dialog.resize(1200, 600)
        dialog.exec_()

    def getOverrides(self):
        """Returns a dictionary of overrides from the various UI elements.

        Returns:
            dict: Override name key and override data values

        """
        overrides = {}
        overrides["RESOLUTION"] = self.default_size_combo_box.currentText()
        overrides["DEPTH"] = self.default_depth_combo_box.currentText()
        overrides["COLORSPACE"] = "No Overrides"
        overrides["POST_PROCESS"] = "No Overrides"
        return overrides

class EditShaderInputsDialog(widgets.QDialog):
    def __init__(self, shader_model_name, current_shader, shader_list, overrides, parent = None):
        widgets.QDialog.__init__(self, parent = parent)

        self._overrides = overrides

        dialog_layout = widgets.QVBoxLayout()
        self.setLayout(dialog_layout)

        # Shader selection
        shader_layout = widgets.QHBoxLayout()
        dialog_layout.addLayout(shader_layout)

        shader_layout.addWidget(widgets.QLabel("Shader:", self))
        self.shader_combobox = widgets.QComboBox(self)
        for shader_name, shader in shader_list:
            self.shader_combobox.addItem(shader_name, shader)
        self.shader_combobox.setCurrentIndex(self.shader_combobox.findData(current_shader))
        self.shader_combobox.currentIndexChanged.connect(self.onShaderInputEditCurrentShaderChanged)
        shader_layout.addWidget(self.shader_combobox)
        hide_unchecked_inputs_button = widgets.QPushButton(mari.resources.createIcon("ViewChecked.svg"), "", self)
        hide_unchecked_inputs_button.setCheckable(True)
        shader_layout.addWidget(hide_unchecked_inputs_button)
        shader_layout.addSpacerItem(widgets.QSpacerItem(0, 0, widgets.QSizePolicy.MinimumExpanding))
        save_preset_button = widgets.QPushButton(mari.resources.createIcon("SaveFile.svg"), "", self)
        save_preset_button.pressed.connect(self.onSavePreset)
        shader_layout.addWidget(save_preset_button)
        load_preset_button = widgets.QPushButton(mari.resources.createIcon("ImportFile.svg"), "", self)
        load_preset_button.pressed.connect(self.onLoadPreset)
        shader_layout.addWidget(load_preset_button)

        # Shader info
        shader_info_layout = widgets.QHBoxLayout()
        shader_info_label = widgets.QLabel("Shader Model - "+shader_model_name, self)
        shader_info_layout.addWidget(shader_info_label)
        shader_info_layout.addSpacerItem(widgets.QSpacerItem(0, 0, widgets.QSizePolicy.MinimumExpanding))
        self.shader_inputs_missing_label_icon = widgets.QLabel(self)
        self.shader_inputs_missing_label_icon.setPixmap(SHADER_ERROR_PIXMAP)
        shader_info_layout.addWidget(self.shader_inputs_missing_label_icon)
        self.shader_inputs_missing_label = widgets.QLabel("No MultiChannelBakePoint or Channel node attached to the Shader", self)
        shader_info_layout.addWidget(self.shader_inputs_missing_label)
        shader_info_layout.addSpacerItem(widgets.QSpacerItem(0, 0, widgets.QSizePolicy.MinimumExpanding))
        dialog_layout.addLayout(shader_info_layout)

        # Export Item Table
        export_item_model = ExportItemModel(mari.geo.list(), self)
        self.export_item_model = export_item_model

        self.export_item_filter_model = ExportItemFilterModel(self)
        self.export_item_filter_model.setSourceModel(export_item_model)
        hide_unchecked_inputs_button.toggled.connect(self.export_item_filter_model.setHideUnchecked)

        export_item_view = mari.system.batch_export_dialog.ExportManagerView()
        self.export_item_view = export_item_view
        export_item_view.setItemDelegate(mari.system.batch_export_dialog.ComboBoxDelegate(parent=self))
        export_item_view.horizontalHeader().setStretchLastSection(True)
        export_item_view.setSelectionBehavior(export_item_view.SelectRows)
        export_item_view.setSelectionMode(export_item_view.ExtendedSelection)
        export_item_view.horizontalHeader().setHighlightSections(False)
        export_item_view.setModel(self.export_item_filter_model)
        export_item_view.setRootIndex(self.export_item_filter_model.mapFromSource(export_item_model.index(0, 0)))
        for index, width in enumerate(mari.system.batch_export_dialog.columnWidths):
            export_item_view.horizontalHeader().resizeSection(index, width)
        dialog_layout.addWidget(export_item_view)

        close_button = widgets.QPushButton("Close", self)
        close_button.pressed.connect(self.accept)
        dialog_layout.addWidget(close_button, alignment = qt.AlignRight)

        # Populate ExportItems + update the stated
        self.onShaderInputEditCurrentShaderChanged()

        # Initial check of validity of export items
        export_item_model.updateStatus()

    def getOverrides(self):
        return self._overrides

    def updateExportItems(self, shader):
        export_items = []
        if shader:
            export_items = getExportItems(shader)

        self.exportItems = set([export_item for export_item, _ in export_items])

        self.export_item_filter_model.setExportItems(self.exportItems)

        return export_items

    def onShaderInputEditCurrentShaderChanged(self):
        current_shader = self.shader_combobox.currentData()

        # We call updateExportItems to populate the export item list of the filter model and also to determine whether to show the warning message
        export_items = self.updateExportItems(current_shader)
        no_inputs = len(export_items)==0
        self.shader_inputs_missing_label.setVisible(no_inputs)
        self.shader_inputs_missing_label_icon.setVisible(no_inputs)

        self.export_item_filter_model.invalidate()

    def onSavePreset(self):
        save_file_name = mari.utils.getSaveFileName(parent=self, caption="Save Export Settings", filter="*.mumm")
        if not save_file_name:
            return

        tree = etree.ElementTree(etree.Element("ExportItems"))
        tree_root = tree.getroot()
        for exportItem in self.exportItems:
            xmlString = exportItem.serializeToString()

            item_root = etree.fromstring(xmlString)
            tree_root.append(item_root)

        tree.write(save_file_name)

    def onLoadPreset(self):
        open_file_name = mari.utils.getOpenFileName(parent=self, caption="Load Export Settings", filter="*.mumm")
        if not open_file_name:
            return

        tree = etree.parse(open_file_name)
        tree_root = tree.getroot()

        NodeAdded = False
        InvalidImportedItemList = []
        for child in tree_root:
            loaded_item = mari.ExportItem()

            loaded_item.deserializeFromString(etree.tostring(child, encoding='unicode'))

            for export_item in self.exportItems:
                if loaded_item.hasMetadata("_STREAM") and export_item.hasMetadata("_STREAM") and loaded_item.metadata("_STREAM") == export_item.metadata("_STREAM"):
                    # Found matching export items. Copy over the values
                    export_item.setExportEnabled( loaded_item.exportEnabled() )
                    export_item.setResolution( loaded_item.resolution() )
                    export_item.setDepth( loaded_item.depth() )
                    export_item.setColorspace( loaded_item.colorspace() )
                    export_item.setPostProcessCommand( loaded_item.postProcessCommand() )
                    export_item.setFileTemplate( loaded_item.fileTemplate() )
                    export_item.setFileOptions( loaded_item.fileOptions() )
                    export_item.setUvIndexList( loaded_item.uvIndexList() )
                    continue

        # Update the model and view
        self.export_item_filter_model.invalidate()


def showUsdMultiShaderExportWidget():
    widget = MultiShaderExportWidget()

    widget.resize(800,600)
    widget.show()
    globals()["USD_MULTI_SHADER_WIDGET"] = widget

if mari.app.isRunning() and mari.projects.current():
    showUsdMultiShaderExportWidget()

