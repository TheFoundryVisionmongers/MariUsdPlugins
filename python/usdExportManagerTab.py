import os
import traceback
import mari
import PySide2.QtCore as core
import PySide2.QtGui as gui
import PySide2.QtWidgets as widgets
from PySide2.QtCore import Qt as qt
from . import usdShadeExport as usd_shade_export

# ==============================================================================
# Defaults
# ==============================================================================

COL_ASSIGN_GEO_ENTITY = 0
COL_ASSIGN_SHADER = 1

COL_EXPORT_SHADER = 0

COL_EXPORT_SHADER_INPUT_NODE = 0
COL_EXPORT_SIZE = 1
COL_EXPORT_COLOR_SPACE = 2
COL_EXPORT_DEPTH = 3
COL_EXPORT_FORMAT = 4

BIT_DEPTHS = {mari.Image.DEPTH_BYTE : "8bit  (Byte)", mari.Image.DEPTH_HALF : "16bit (Half)", mari.Image.DEPTH_FLOAT: "32bit (Float)"}

EXPORT_OVERRIDES = [None] * 5

# ==============================================================================
# Shader Panel
# ==============================================================================

def get_relevant_shaders(geo_entity):
    return [shader for shader in geo_entity.shaderList() if not shader.isSystemShader()]

class ShaderAssignment_Item(gui.QStandardItem):
    def __init__(self, source_object = None):
        gui.QStandardItem.__init__(self)
        self.setData(source_object, qt.UserRole)

    def set_geo_entity_meta_data(self, value):
        index = self.index()
        if not index.isValid():
            return
        
        column = index.column()
        if column != COL_ASSIGN_SHADER:
            return
            
        model = index.model()
        if not model:
            return

        geo_entity_item = model.item(index.row(), COL_ASSIGN_GEO_ENTITY)
        if not geo_entity_item:
            return
            
        geo_entity = geo_entity_item.data(qt.UserRole)
        if not geo_entity:
            return
        
        source_node_uuid = ""
        if value:
            source_node = value.shaderNode()
            if source_node:
                source_node_uuid = source_node.uuid()
        
        geo_entity.setMetadata("UsdShaderNodeUuid", source_node_uuid)

    def setData(self, value, role):
        if role == qt.UserRole:
            self.set_geo_entity_meta_data(value)
            
        gui.QStandardItem.setData(self, value, role)

    def data(self, role):
        if role == qt.DisplayRole:
            source_object = self.data(qt.UserRole)
            if source_object:
                return source_object.name()
            return ""

        return gui.QStandardItem.data(self, role)

class ShaderAssignment_ItemDelegate(widgets.QStyledItemDelegate):
    def __init__(self, parent = None):
        widgets.QStyledItemDelegate.__init__(self, parent = parent)

    def createEditor(self, parent, option, index):
        if index.column() == COL_ASSIGN_SHADER:
            model = index.model()
            geo_entity = model.item(index.row(), COL_ASSIGN_GEO_ENTITY).data(qt.UserRole)
            
            editor = widgets.QComboBox(parent)
            if geo_entity:
                for geo_entity_shader in get_relevant_shaders(geo_entity):
                    editor.addItem(geo_entity_shader.name(), geo_entity_shader)

            editor.currentIndexChanged.connect(self.finishEdit)

            return editor

        return widgets.QStyledItemDelegate.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        if index.column() == COL_ASSIGN_SHADER and isinstance(editor, widgets.QComboBox):
            model = index.model()
            geo_entity = model.item(index.row(), COL_ASSIGN_GEO_ENTITY).data(qt.UserRole)
            shader = model.itemFromIndex(index).data(qt.UserRole)
            source_node_uuid = ""
            if shader and geo_entity:
                source_node = shader.shaderNode()
                if source_node:
                    source_node_uuid = source_node.uuid()
                
                try:
                    editor.setCurrentIndex(get_relevant_shaders(geo_entity).index(shader))
                except ValueError:
                    pass
                    
            if geo_entity:
                geo_entity.setMetadata("UsdShaderNodeUuid", source_node_uuid)
                
            return

        widgets.QStyledItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        if index.column() == COL_ASSIGN_SHADER and isinstance(editor, widgets.QComboBox):
            geo_entity = model.item(index.row(), COL_ASSIGN_GEO_ENTITY).data(qt.UserRole)
            shader = editor.itemData(editor.currentIndex(), qt.UserRole)
            model.itemFromIndex(index).setData(shader, qt.UserRole)
            return

        widgets.QStyledItemDelegate.setModelData(self, editor, model, index)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def finishEdit(self):
        editor = self.sender()
        if isinstance(editor, widgets.QComboBox):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, self.NoHint)

class ShaderAssignment_Model(gui.QStandardItemModel):
    def __init__(self, parent = None):
        gui.QStandardItemModel.__init__(self, parent = parent)

        geo_manager = mari.geo
        
        self._refresh_geo_entity_list(True, False)
        
        mari.utils.connect(geo_manager.entityAdded, self._on_geo_entity_added)
        mari.utils.connect(geo_manager.entityRemoved, self._on_geo_entity_removed)

    def parentObject(self):
        return core.QObject.parent(self)

    def flags(self, index = core.QModelIndex()):
        flags = gui.QStandardItemModel.flags(self, index)
        column = index.column()
        if column == COL_ASSIGN_GEO_ENTITY:
            flags = flags |  qt.ItemIsUserCheckable
            flags = flags & ~qt.ItemIsEditable
        elif column == COL_ASSIGN_SHADER:
            flags = flags |  qt.ItemIsEditable
            flags = flags & ~qt.ItemIsUserCheckable
        else:
            flags = flags & ~(qt.ItemIsEditable | qt.ItemIsUserCheckable)
        return flags

    def headerData(self, section, orientation, role):
        if orientation == qt.Horizontal:
            if role == qt.DisplayRole:
                if section == COL_ASSIGN_GEO_ENTITY:
                    return "Object"
                elif section == COL_ASSIGN_SHADER:
                    return "Shader"
            elif role == qt.TextAlignmentRole:
                return qt.AlignHCenter
        return None
        
    def selected_shaders(self):
        shader_list = []
        for row in range(self.rowCount()):
            geo_entity_item = self.item(row, COL_ASSIGN_GEO_ENTITY)
            if qt.Checked == geo_entity_item.data(qt.CheckStateRole):
                shader_item = self.item(row, COL_ASSIGN_SHADER)
                shader = shader_item.data(qt.UserRole)
                if shader:
                    shader_list.append(shader)
        return shader_list

    def _refresh_geo_entity_list(self, added = True, removed = True):
        new_geo_entities = mari.geo.list()

        # Delete any geo entities that were removed.
        if removed:
            for old_row in range(self.rowCount()-1, -1, -1):
                if self.item(old_index, COL_ASSIGN_GEO_ENTITY).data(qt.UserRole) not in new_geo_entities:
                    row_items = self.takeRow(old_row)
                    del row_items

        # Add any new or move existing geo entities.
        if added:
            for new_row, new_geo_entity in enumerate(new_geo_entities):
                for old_row in range(self.rowCount()):
                    if self.item(old_row, COL_ASSIGN_GEO_ENTITY).data(qt.UserRole) == new_geo_entity:
                        # Already exists, move if necessary.
                        if new_row != old_row:
                            self.insertRow(new_row, self.takeRow(old_row))
                        break
                else:
                    # Doesn't already exist, add it.
                    new_geo_entity_item = ShaderAssignment_Item(new_geo_entity)
                    new_geo_entity_item.setData(qt.Checked, qt.CheckStateRole)
                    shaders = get_relevant_shaders(new_geo_entity)
                    
                    default_shader = None if len(shaders) == 0 else shaders[0]
                    if new_geo_entity.hasMetadata("UsdShaderNodeUuid"):
                        saved_uuid = new_geo_entity.metadata("UsdShaderNodeUuid")
                        for shader in shaders:
                            node = shader.shaderNode()
                            if node and node.uuid() == saved_uuid:
                                default_shader = shader
                                break
                    
                    new_shader_item = ShaderAssignment_Item(default_shader)
                    
                    self.insertRow(new_row, [new_geo_entity_item, new_shader_item])
                    
                    # mari.utils.connect(new_geo_entity.shaderCreated, self._on_shader_created)
                    mari.utils.connect(new_geo_entity.shaderCreated, self._on_shader_removed)

    def _on_geo_entity_added(self, entity):
        self._refresh_geo_entity_list(True, False)

    def _on_geo_entity_removed(self, entity):
        self._refresh_geo_entity_list(False, True)
        
    def _on_shader_created(self, shader):
        # Don't actually care if shaders are added, the user would need to select them to have any effect.
        pass
    
    def _on_shader_removed(self, shader):
        geo_entity = self.sender()
        for row in range(self.rowCount()):
            if geo_entity == self.item(row, COL_ASSIGN_GEO_ENTITY).data(qt.UserRole):
                shader_item = self.item(row, COL_ASSIGN_SHADER)
                if shader_item.data(qt.UserRole) not in get_relevant_shaders(geo_entity):
                    shader_item.setData(None, qt.UserRole)
                break

class ShaderAssignment_View(widgets.QTableView):
    def __init__(self, parent = None):
        widgets.QTableView.__init__(self, parent = parent)
        self.horizontalHeader().setSectionResizeMode(widgets.QHeaderView.Stretch)
        self.setEditTriggers(widgets.QAbstractItemView.CurrentChanged | widgets.QAbstractItemView.SelectedClicked | widgets.QAbstractItemView.DoubleClicked)

# ==============================================================================
# Export Item Panel
# ==============================================================================

def split_ext(path):
    file_name, file_ext = os.path.splitext(path)
    file_ext = file_ext[1:].lower() if len(file_ext) > 0 and file_ext[0] == '.' else file_ext.lower()
    return file_name, file_ext

class ExportItem_ShaderItem(gui.QStandardItem):
    def __init__(self, source_object = None):
        gui.QStandardItem.__init__(self)
        self.setData(source_object, qt.UserRole)

    def data(self, role):
        if role == qt.DisplayRole:
            source_object = self.data(qt.UserRole)
            if source_object:
                return source_object.name()
            return ""
    
        return gui.QStandardItem.data(self, role)
        
class ExportItem_ShaderInputItem(gui.QStandardItem):
    def __init__(self, source_object = None, text = "", input_name = ""):
        gui.QStandardItem.__init__(self, text)
        self.setData(source_object, qt.UserRole)
        self.setData(None, qt.UserRole+1)
        self.setData(input_name, qt.UserRole+2)

    def setData(self, data, role):
        if role == qt.CheckStateRole:
            export_item = self.data(qt.UserRole+1)
            if export_item:
                if qt.Unchecked == data:
                    export_item.setExportEnabled(False)
                else:
                    export_item.setExportEnabled(True)
        
        gui.QStandardItem.setData(self, data, role)

    def data(self, role):
        if role == qt.CheckStateRole:
            export_item = self.data(qt.UserRole+1)
            if export_item and export_item.exportEnabled():
                return qt.Checked
            else:
                return qt.Unchecked
    
        return gui.QStandardItem.data(self, role)

class ExportItem_SettingsItem(gui.QStandardItem):
    def __init__(self, data = None, text = None):
        gui.QStandardItem.__init__(self)
        self.setData(data, qt.UserRole)
        if text:
            self.setData(text, qt.DisplayRole)
        
    def _export_item(self):
        index = self.index()
        if index.column() == COL_EXPORT_SHADER_INPUT_NODE:
            return self.data(qt.UserRole+1)
            
        shader_input_index = index.sibling(index.row(), COL_EXPORT_SHADER_INPUT_NODE)
        shader_input_item = index.model().itemFromIndex(shader_input_index)
        if shader_input_item:
            return shader_input_item.data(qt.UserRole+1)

        return None

    def data(self, role):
        if role == qt.DisplayRole:
            column = self.index().column()
            if column >= 1 and column <= 4:
                override = self.model().override(column)
                export_item = self._export_item()
                if export_item:
                    if column == COL_EXPORT_SIZE:
                        export_item_res = export_item.resolution() if override is None else override
                        if export_item_res == mari.exports.resolutionList()[0]:
                            export_item_res += " (%s)" % export_item.sourceResolution()
                        return export_item_res
                    elif column == COL_EXPORT_COLOR_SPACE:
                        export_item_color_space = export_item.colorspace() if override is None else override
                        if export_item_color_space == mari.exports.colorspaceList()[0]:
                            export_item_color_space += " (%s)" % export_item.sourceColorspace()
                        return export_item_color_space
                    elif column == COL_EXPORT_DEPTH:
                        export_item_depth = export_item.depth() if override is None else override
                        if export_item_depth == mari.exports.depthList()[0]:
                            export_item_depth += " (%s)" % BIT_DEPTHS[export_item.sourceDepth()]
                        return export_item_depth
                    elif column == COL_EXPORT_FORMAT:
                        file_name, file_ext = split_ext(export_item.fileTemplate())
                        return file_ext

        return gui.QStandardItem.data(self, role)

    def setData(self, data, role):
        if role == qt.UserRole:
            column = self.index().column()
            if column >= 1 and column <= 4:
                export_item = self._export_item()
                if export_item:
                    if column == COL_EXPORT_SIZE:
                        export_item.setResolution(data)
                    elif column == COL_EXPORT_COLOR_SPACE:
                        export_item.setColorspace(data)
                    elif column == COL_EXPORT_DEPTH:
                        export_item.setDepth(data)
                    elif column == COL_EXPORT_FORMAT:
                        file_name, file_ext = split_ext(export_item.fileTemplate())
                        export_item.setFileTemplate("%s.%s" % (file_name, data))
                    return
            
        gui.QStandardItem.setData(self, data, role)

class ExportItem_ItemDelegate(widgets.QStyledItemDelegate):
    def __init__(self, parent = None):
        widgets.QStyledItemDelegate.__init__(self, parent = parent)

    def createEditor(self, parent, option, index):
        column = index.column()
        if column >= 1 and column <= 4:
            model = index.model()
            export_item = model.itemFromIndex(index)._export_item()

            if column == COL_EXPORT_SIZE:
                editor = widgets.QComboBox(parent)                
                for i, size in enumerate(mari.exports.resolutionList()):
                    if i == 0:
                        export_item_res = export_item.resolution()
                        if export_item_res == size:
                            export_item_res = export_item.sourceResolution()
                        editor.addItem(size + " (%s)" % export_item_res, size)
                    else:
                        editor.addItem(size, size)
                editor.currentIndexChanged.connect(self.finishEdit)
                return editor
            elif column == COL_EXPORT_COLOR_SPACE:
                editor = widgets.QComboBox(parent)
                for i, color_space in enumerate(mari.exports.colorspaceList()):
                    if i == 0:
                        export_item_color_space = export_item.colorspace()
                        if export_item_color_space == color_space:
                            export_item_color_space = export_item.sourceColorspace()
                        editor.addItem(color_space + " (%s)" % export_item_color_space, color_space)
                    else:
                        editor.addItem(color_space, color_space)
                editor.currentIndexChanged.connect(self.finishEdit)
                return editor
            elif column == COL_EXPORT_DEPTH:
                editor = widgets.QComboBox(parent)
                for i, depth in enumerate(mari.exports.depthList()):
                    if i == 0:
                        export_item_depth = export_item.depth()
                        if export_item_depth == depth:
                            export_item_depth = export_item.sourceDepth()
                        editor.addItem(depth + " (%s)" % BIT_DEPTHS[export_item_depth], depth)
                    else:
                        editor.addItem(depth, depth)
                editor.currentIndexChanged.connect(self.finishEdit)
                return editor
            elif column == COL_EXPORT_FORMAT:
                editor = widgets.QComboBox(parent)
                for format in mari.exports.imageFileExtensionList():
                    editor.addItem(format.upper(), format)
                editor.currentIndexChanged.connect(self.finishEdit)
                return editor

        return widgets.QStyledItemDelegate.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, widgets.QComboBox):
            column = index.column()
            if column >= 1 and column <= 4:
                current_value = None
                current_index = 0

                model = index.model()
                export_item = model.itemFromIndex(index)._export_item()
                
                if column == COL_EXPORT_SIZE:
                    current_value = export_item.resolution()
                elif column == COL_EXPORT_COLOR_SPACE:
                    current_value = export_item.colorspace()
                elif column == COL_EXPORT_DEPTH:
                    current_value = export_item.depth()
                elif column == COL_EXPORT_FORMAT:
                    file_name, file_ext = split_ext(export_item.fileTemplate())
                    current_value = file_ext
                
                for combo_box_index in range(editor.count()):
                    if editor.itemData(combo_box_index) == current_value:
                        current_index = combo_box_index
                        break

                editor.setCurrentIndex(current_index)
                return

        widgets.QStyledItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, widgets.QComboBox):
            column = index.column()
            if column >= 1 and column <= 4:
                model.itemFromIndex(index).setData(editor.itemData(editor.currentIndex()), qt.UserRole)
                return

        widgets.QStyledItemDelegate.setModelData(self, editor, model, index)

    def finishEdit(self):
        editor = self.sender()
        if isinstance(editor, widgets.QComboBox):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, self.NoHint)

class ExportItem_Model(gui.QStandardItemModel):
    def __init__(self, parent = None):
        gui.QStandardItemModel.__init__(self, parent)
        
        self.export_overrides = [None]*5

    def parentObject(self):
        return core.QObject.parent(self)

    def override(self, index):
        return self.export_overrides[index]

    def setOverride(self, index, value):
        self.export_overrides[index] = value

    def update_shader_items(self, new_shader_list):
        added_rows = []
        if len(new_shader_list) == 0:
            self.clear()
        else:        
            for old_row in range(self.rowCount()-1, -1, -1):
                shader_item = self.item(old_row, COL_EXPORT_SHADER)
                if shader_item:
                    shader = shader_item.data(qt.UserRole)
                    if shader not in new_shader_list:
                        row_items = self.takeRow(old_row)
                        del row_items
            
            for new_row, new_shader in enumerate(new_shader_list):
                for old_row in range(self.rowCount()):
                    shader_item = self.item(old_row, COL_EXPORT_SHADER)
                    if shader_item:
                        shader = shader_item.data(qt.UserRole)
                        if shader == new_shader:
                            if new_row != old_row:
                                self.insertRow(new_row, self.takeRow(old_row))
                            break
                else:
                    shader_item = ExportItem_ShaderItem(new_shader)
                    self.insertRow(new_row, [shader_item,])
                    self.updateShaderInputs(shader_item)
                    added_rows.append(shader_item)
        return added_rows

    def _advancedInputList(self, shader):
        result = []
        shader_node = shader.shaderNode()
        shader_model = shader.shaderModel()
        for input_name in shader_node.inputPortNames():
            input_node, output_port = shader_node.inputConnection(input_name)
            if input_node:
                shader_model_input = shader_model.input(input_name)
                shader_model_input_name = shader_model_input.name()

                if isinstance(input_node, mari.GroupNode):
                    output_node = input_node.groupOutputNode(output_port)
                    if output_node:
                        input_node = output_node.inputNode("Input")
                    else:
                        input_node = None

                    if not input_node:
                        continue

                if isinstance(input_node, mari.ChannelNode):
                    result.append((input_name, input_node, shader_model_input_name))
                elif isinstance(input_node, mari.BakePointNode):
                    result.append((input_name, input_node, shader_model_input_name))
        
        return result

    def updateShaderInputs(self, shader_item):
        new_shader_input_infos = []
        shader_input_set = set()
        node_to_export_item = {}
        
        shader = shader_item.data(qt.UserRole)
        if shader:            
            new_shader_input_infos = self._advancedInputList(shader)
            for input_name, shader_input, shader_input_name in new_shader_input_infos:
                shader_input_set.add(shader_input)
        
        if len(new_shader_input_infos) == 0:
            row_count = shader_item.rowCount()
            if row_count > 0:
                shader_item.removeRows(0, row_count)
            shader_item.insertRow(0, [gui.QStandardItem("No Channels to Export"),])
            return
        
        for old_row in range(shader_item.rowCount()-1, -1, -1):
            child = shader_item.child(old_row, COL_EXPORT_SHADER_INPUT_NODE)
            if child and child.data(qt.UserRole) not in shader_input_set:
                row_items = shader_item.takeRow(old_row)
                del row_items
        
        for new_row, shader_input_info in enumerate(new_shader_input_infos):
            input_name, shader_input, shader_input_name = shader_input_info
            for old_row in range(shader_item.rowCount()):
                child = shader_item.child(old_row, COL_EXPORT_SHADER_INPUT_NODE)
                if child and child.data(qt.UserRole) == shader_input:
                    if new_row != old_row:
                        shader_item.insertRow(new_row, shader_item.takeRow(old_row))
                    break
            else:
                shader_input_item = ExportItem_ShaderInputItem(shader_input, input_name, shader_input_name)
                size_item = ExportItem_SettingsItem()
                colorspace_item = ExportItem_SettingsItem()
                depth_item = ExportItem_SettingsItem()
                file_options = ExportItem_SettingsItem()
                
                shader_item.insertRow(new_row, [shader_input_item, size_item, colorspace_item, depth_item, file_options])

        self.update_export_items(shader_item)

    def update_export_items(self, shader_item, geo_entity = None):
        if geo_entity is None:
            shader = shader_item.data(qt.UserRole)
            if shader:
                node = shader.shaderNode()
                if node:
                    geo_entity = node.parentNodeGraph().parentGeoEntity()
            if geo_entity is None:
                return

        for row in range(shader_item.rowCount()):
            self.update_child_export_item(shader_item, row, geo_entity)

    def update_child_export_item(self, shader_item, row, geo_entity = None):
        if geo_entity is None:
            shader = shader_item.data(qt.UserRole)
            if shader:
                node = shader.shaderNode()
                if node:
                    geo_entity = node.parentNodeGraph().parentGeoEntity()
            if geo_entity is None:
                return

        shader_input_item = shader_item.child(row, COL_EXPORT_SHADER_INPUT_NODE)
        
        self.update_export_item(shader_input_item, geo_entity)
        
    def update_export_item(self, shader_input_item, geo_entity = None):
        if geo_entity is None:
            shader_input_node = shader_input_item.data(qt.UserRole)
            if shader_input_node:
                parent_graph = shader_input_node.parentNodeGraph()
                if parent_graph:
                    geo_entity = parent_graph.parentGeoEntity()
            if geo_entity is None:
                return

        if shader_input_item:
            shader_input_node_export_item = shader_input_item.data(qt.UserRole+1)
            if shader_input_node_export_item is None:
                shader_input_node = shader_input_item.data(qt.UserRole)
                if shader_input_node:
                    for export_item in mari.exports.exportItemList(geo_entity):
                        if export_item and export_item.sourceNode() == shader_input_node:
                            shader_input_item.setData(export_item, qt.UserRole+1)
                            break
                    else:
                        # Create new export item if required.
                        if shader_input_node_export_item is None:
                            shader_input_node_export_item = mari.ExportItem()
                            shader_input_node_export_item.setSourceNode(shader_input_node)
                            shader_input_node_export_item.setFileTemplate(self.parentObject().default_texture_pattern)
                            shader_input_node_export_item.setMetadata("_HIDDEN", True)
                            mari.exports.addExportItem(shader_input_node_export_item, geo_entity)
                            shader_input_item.setData(shader_input_node_export_item, qt.UserRole+1)

    def update_column(self, column):
        for row in range(self.rowCount()):
            shader_item = self.item(row, 0)
            if shader_item:
                for child_row in range(shader_item.rowCount()):
                    child = shader_item.child(child_row, column)
                    if child:
                        child.emitDataChanged()

    def flags(self, index = core.QModelIndex()):
        flags = gui.QStandardItemModel.flags(self, index)
        
        column = index.column()
        valid_parent = index.parent().isValid()
        if valid_parent and column == COL_EXPORT_SHADER:
            flags = flags |  qt.ItemIsUserCheckable
            flags = flags & ~qt.ItemIsEditable
        else:
            if valid_parent and self.override(column) is None:
                flags = flags |  qt.ItemIsEditable
            else:
                flags = flags & ~qt.ItemIsEditable
            flags = flags & ~qt.ItemIsUserCheckable
        return flags
        
    def columnCount(self, index = core.QModelIndex()):
        return 5

    def headerData(self, section, orientation, role):
        if orientation == qt.Horizontal:
            if role == qt.DisplayRole:
                if section == COL_EXPORT_SHADER or section == COL_EXPORT_SHADER_INPUT_NODE:
                    return "Shader / Export Item"
                elif section == COL_EXPORT_SIZE:
                    return "Size"
                elif section == COL_EXPORT_COLOR_SPACE:
                    return "Color Space"
                elif section == COL_EXPORT_DEPTH:
                    return "Depth"
                elif section == COL_EXPORT_FORMAT:
                    return "Format"
            elif role == qt.TextAlignmentRole:
                return qt.AlignHCenter
        return None

    def data(self, index, role):
        if role == qt.ForegroundRole:
            if index.parent().isValid():
                if self.override(index.column()) is not None:
                    return gui.QColor(50, 50, 50)
        if role == qt.BackgroundRole:
            if index.parent().isValid():
                if self.override(index.column()) is not None:
                    return gui.QColor(200, 157, 0)
        return gui.QStandardItemModel.data(self, index, role)

    def get_items_for_export(self):
        for_export = {}
        export_item_to_shader_input_name = {}
        for row in range(self.rowCount()):
            shader_item = self.item(row, COL_EXPORT_SHADER)
            shader = shader_item.data(qt.UserRole)
            if shader:
                export_items = []
                for child_row in range(shader_item.rowCount()):
                    shader_input_item = shader_item.child(child_row, COL_EXPORT_SHADER_INPUT_NODE)
                    export_item = shader_input_item.data(qt.UserRole+1)
                    shader_input_name = shader_input_item.data(qt.UserRole+2)
                    if export_item and export_item.exportEnabled():
                        export_items.append((export_item, shader_input_name))
                
                if len(export_items) > 0:
                    for_export[shader] = export_items

        return for_export

class ExportItem_View(widgets.QTreeView):
    def __init__(self, parent = None):
        widgets.QTreeView.__init__(self, parent = parent)
        self.header().setSectionResizeMode(widgets.QHeaderView.Stretch)
        self.setUniformRowHeights(True)
        self.setEditTriggers(widgets.QAbstractItemView.CurrentChanged | widgets.QAbstractItemView.SelectedClicked | widgets.QAbstractItemView.DoubleClicked)

# ==============================================================================
# Main Widget
# ==============================================================================

class FileBrowseWidget(widgets.QWidget):
    pathChanged = core.Signal(str)
    
    def __init__(self, parent = None, type = widgets.QFileDialog.AnyFile, filters = "", history = []):
        widgets.QWidget.__init__(self, parent)
        self.history = history
        self.type = type
        self.filters = filters
        
        self.file_system_model = widgets.QFileSystemModel()
        self.file_system_model.setRootPath(core.QDir.rootPath())
        self.completer = widgets.QCompleter()
        self.completer.setModel(self.file_system_model)
        self.completer.setCompletionMode(widgets.QCompleter.PopupCompletion)
        
        layout = widgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.combo_box = widgets.QComboBox()
        self.combo_box.setCompleter(self.completer)
        self.combo_box.setEditable(True)
        self.combo_box.setSizePolicy(widgets.QSizePolicy.Expanding, widgets.QSizePolicy.Fixed)
        self.combo_box.setMaximumHeight(32)
        self.adding_paths = True
        self.combo_box.addItems(self.history)
        self.adding_paths = False
        self.browse_button = widgets.QPushButton("...")
        self.browse_button.setMaximumSize(32, 32)
        layout.addWidget(self.combo_box)
        layout.addWidget(self.browse_button)
        
        self.setLayout(layout)
        
        mari.utils.connect(self.combo_box.lineEdit().editingFinished, self.on_combo_box_editing_finished)
        mari.utils.connect(self.combo_box.currentIndexChanged, self.on_combo_box_index_changed)
        mari.utils.connect(self.browse_button.pressed, self.browse)
        
    def path(self):
        if len(self.history) > 0:
            return self.history[0]
        return ""
        
    def paths(self):
        return self.history
        
    def browse(self):
        if self.type == widgets.QFileDialog.Directory:
            new_path = mari.utils.misc.getExistingDirectory(self, "Select Directory", self.path())
        elif self.type == widgets.QFileDialog.ExistingFile:
            new_path = mari.utils.misc.getOpenFileName(self, "Select File", self.path(), self.filters)
        else:
            new_path = mari.utils.misc.getSaveFileName(self, "Select File", self.path(), self.filters, save_filename=self.path())

        if len(new_path) == 0:
            return

        self.new_path_added(new_path)

    def on_combo_box_editing_finished(self):
        if self.adding_paths:
            return

        self.new_path_added(self.combo_box.lineEdit().text())

    def on_combo_box_index_changed(self, index):
        if self.adding_paths:
            return

        self.new_path_added(self.combo_box.itemText(index))

    def new_path_added(self, new_path):
        if len(new_path) == 0:
            return

        old_path = self.path()
        
        try:
            index = self.history.index(new_path)
        except ValueError:
            self.history.insert(0, new_path)
        else:
            self.history.insert(0, self.history.pop(index))
        
        self.adding_paths = True
        self.combo_box.clear()
        self.combo_box.addItems(self.history)
        self.combo_box.setCurrentIndex(0)
        self.adding_paths = False
        
        if old_path != new_path:
            self.pathChanged.emit(new_path)

class USDExportWidget(widgets.QWidget):
    def __init__(self, parent = None):
        widgets.QWidget.__init__(self, parent)

        main_layout = widgets.QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(3, 3, 3, 3)

        shader_export_item_layout = widgets.QSplitter(qt.Vertical)
        
        self.default_size = mari.exports.resolutionList()[1]
        self.default_color_space = mari.exports.colorspaceList()[1]
        self.default_depth = mari.exports.depthList()[1]
        formats = mari.exports.imageFileExtensionList()
        self.default_format = "tif" if "tif" in formats else formats[0]
        self.default_texture_pattern = "$CHANNEL.$UDIM.%s" % self.default_format

        self.shader_assignment_view = ShaderAssignment_View(parent=self)
        self.shader_assignment_model = ShaderAssignment_Model(parent=self)
        self.shader_assignment_view.setModel(self.shader_assignment_model)
        self.shader_assignment_view.setItemDelegate(ShaderAssignment_ItemDelegate(parent=self))
        shader_export_item_layout.addWidget(self.shader_assignment_view)

        self.export_item_view = ExportItem_View(parent=self)
        self.export_item_model = ExportItem_Model(parent=self)
        self.export_item_view.setModel(self.export_item_model)
        self.export_item_view.setItemDelegate(ExportItem_ItemDelegate(parent=self))
        shader_export_item_layout.addWidget(self.export_item_view)
        
        main_layout.addWidget(shader_export_item_layout)

        # USD Export Options
        options_group_box = widgets.QGroupBox(self)
        options_group_box.setSizePolicy(widgets.QSizePolicy.Expanding, widgets.QSizePolicy.Fixed)
        options_layout = widgets.QGridLayout(options_group_box)
        options_layout.setContentsMargins(3, 3, 3, 3)
        options_layout.setHorizontalSpacing(5)
        options_layout.setVerticalSpacing(15)
        for index, stretch in enumerate((10, 20, 10, 20)):
            options_layout.setColumnStretch(index, stretch)

        self.export_usd_target_dir_widget = FileBrowseWidget(self, widgets.QFileDialog.Directory, "", self.load_usd_target_dir_paths())
        target_dir_label = widgets.QLabel("Target Directory", self)
        target_dir_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(target_dir_label, 0, 0)
        options_layout.addWidget(self.export_usd_target_dir_widget, 0, 1)
        
        self.default_depth_combo_box = widgets.QComboBox(self)
        self.default_depth_combo_box.setSizePolicy(widgets.QSizePolicy.Expanding, widgets.QSizePolicy.Fixed)
        self.default_depth_combo_box.addItem("No Override", None)
        self.default_depth_combo_box.setToolTip("Overrides the bit depth of exported export items.\nWill not change export item until Export is triggered, will not change export items which are not exported.")
        for depth in mari.exports.depthList():
            self.default_depth_combo_box.addItem(depth, depth)
        override_depth_label = widgets.QLabel("Override Depth", self)
        override_depth_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(override_depth_label, 0, 2)
        options_layout.addWidget(self.default_depth_combo_box, 0, 3)
        
        image_filter = "Images (" + " ".join(["*.%s" % ext for ext in mari.exports.imageFileExtensionList()]) + ")"
        self.export_texture_file_widget = FileBrowseWidget(self, widgets.QFileDialog.AnyFile, image_filter, self.load_usd_texture_file_paths())
        export_texture_file_label = widgets.QLabel("Texture File Name", self)
        export_texture_file_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(export_texture_file_label, 1, 0)
        options_layout.addWidget(self.export_texture_file_widget, 1, 1)
        
        self.default_size_combo_box = widgets.QComboBox(self)
        self.default_size_combo_box.setSizePolicy(widgets.QSizePolicy.Expanding, widgets.QSizePolicy.Fixed)
        self.default_size_combo_box.addItem("No Override", None)
        self.default_size_combo_box.setToolTip("Overrides the resolution of exported export items.\nWill not change export item until Export is triggered, will not change export items which are not exported.")
        for size in mari.exports.resolutionList():
            self.default_size_combo_box.addItem(size, size)
        override_resolution_label = widgets.QLabel("Override Resolution", self)
        override_resolution_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(override_resolution_label, 1, 2)
        options_layout.addWidget(self.default_size_combo_box, 1, 3)
        
        look_file_filter = "USD Look File (*.usd *.usda *.usdz)"
        self.look_file_widget = FileBrowseWidget(self, widgets.QFileDialog.AnyFile, look_file_filter, self.load_usd_look_file_paths())
        look_file_label = widgets.QLabel("USD Look File", self)
        look_file_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(look_file_label, 2, 0)
        options_layout.addWidget(self.look_file_widget, 2, 1)
        
        self.root_name_widget = widgets.QLineEdit(self)
        self.root_name_widget.setText(self.load_root_name(default_root_name="Root"))
        root_name_label = widgets.QLabel("Root Name", self)
        root_name_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(root_name_label, 2, 2)
        options_layout.addWidget(self.root_name_widget, 2, 3)
        
        assembly_file_filter = "USD Assembly File (*.usd *.usda *.usdz)"
        self.assembly_file_widget = FileBrowseWidget(self, widgets.QFileDialog.AnyFile, assembly_file_filter, self.load_usd_assembly_file_paths())
        assembly_file_label= widgets.QLabel("USD Assembly File", self)
        assembly_file_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(assembly_file_label, 3, 0)
        options_layout.addWidget(self.assembly_file_widget, 3, 1)
        
        payload_file_filter = "USD (*.usd *.usda *.usdz)"
        self.payload_file_widget = FileBrowseWidget(self, widgets.QFileDialog.ExistingFile, payload_file_filter, self.load_usd_payload_file_paths())
        payload_label = widgets.QLabel("USD Payload", self)
        payload_label.setAlignment(qt.AlignRight | qt.AlignVCenter)
        options_layout.addWidget(payload_label, 3, 2)
        options_layout.addWidget(self.payload_file_widget, 3, 3)
        
        main_layout.addWidget(options_group_box)
        
        export_layout = widgets.QHBoxLayout()
        self.export_button = widgets.QPushButton("Export to USD")
        export_layout.addWidget(self.export_button)
        main_layout.addLayout(export_layout)
        for index, stretch in enumerate((20, 10, 5)):
            main_layout.setStretch(index, stretch)
        
        self.export_item_view.expandAll()
        self.on_shader_assignment_changed(None)
        
        mari.utils.connect(self.shader_assignment_model.itemChanged, self.on_shader_assignment_changed)
        mari.utils.connect(self.default_depth_combo_box.currentIndexChanged, self.on_default_depth_combo_box_changed)
        mari.utils.connect(self.export_texture_file_widget.pathChanged, self.on_export_texture_file_name_widget_path_changed)
        mari.utils.connect(self.default_size_combo_box.currentIndexChanged, self.on_default_size_combo_box_changed)
        mari.utils.connect(self.export_button.pressed, self.on_export_button_pressed)

    def load_paths(self, name, default_path):
        # Pull the path history from the settings.
        settings = mari.Settings()
        paths = []
        settings_paths = settings.value("UsdExportDialog/%s" % name)
        if isinstance(settings_paths, str):
            paths.append(settings_paths)
        elif isinstance(settings_paths, list):
            paths = settings_paths

        # If the project has a path saved with it, put that first in the list.
        project = mari.projects.current()
        if project:
            if project.hasMetadata(name):
                project_path = str(project.metadata(name))
                if len(project_path) > 0:
                    try:
                        index = paths.index(project_path)
                    except ValueError:
                        paths.insert(0, project_path)
                    else:
                        paths.insert(0, paths.pop(index))

        if len(paths) == 0:
            # If the list is empty, add the default path.
            paths.insert(0, default_path)
        elif len(paths[0]) == 0:
            # If the first entry in the list is empty, replace it with the default path.
            paths[0] = default_path
            
        return paths

    def load_usd_target_dir_paths(self):
        default = mari.resources.path("MARI_DEFAULT_EXPORT_PATH")
        return self.load_paths("UsdTargetDirPaths", default)

    def load_usd_texture_file_paths(self):
        default = os.path.join(mari.resources.path("MARI_DEFAULT_EXPORT_PATH"), self.default_texture_pattern)
        return self.load_paths("UsdTexturePaths", default)

    def load_usd_look_file_paths(self):
        default = os.path.join(mari.resources.path("MARI_DEFAULT_EXPORT_PATH"), "Look File.usda")
        return self.load_paths("UsdLookPaths", default)
        
    def load_usd_assembly_file_paths(self):
        default = os.path.join(mari.resources.path("MARI_DEFAULT_EXPORT_PATH"), "Assembly.usda")
        return self.load_paths("UsdAssemblyPaths", default)

    def load_usd_payload_file_paths(self):
        default = os.path.join(mari.resources.path("MARI_DEFAULT_EXPORT_PATH"), "Payload.usd")
        return self.load_paths("UsdPayloadPaths", default)
        
    def load_root_name(self, default_root_name):
        name = "UsdRootName"

        project = mari.projects.current()
        if project:
            if project.hasMetadata(name):
                project_root_name = project.metadata(name)

                if len(project_root_name) != 0:
                    return project_root_name

        settings_root_name = str(mari.Settings().value("UsdExportDialog/%s" % name))
        if len(settings_root_name) != 0:
            return settings_root_name

        return default_root_name
        
    def on_default_depth_combo_box_changed(self, text):
        self.on_default_depth_changed(text)

    def on_default_size_combo_box_changed(self, text):
        self.on_default_size_changed(text)

    def on_export_texture_file_name_widget_path_changed(self, path):
        file_name, file_ext = split_ext(path)
        self.default_format = file_ext
        self.default_texture_pattern = path

    def on_export_texture_file_name_browse_button_pressed(self):
        pass

    def on_default_size_changed(self, index):
        editor = self.sender()
        if isinstance(editor, widgets.QComboBox):
            size = editor.itemData(index)
            self.export_item_model.setOverride(COL_EXPORT_SIZE, size)
            self.export_item_model.update_column(COL_EXPORT_SIZE)
        
    def on_default_depth_changed(self, index):
        editor = self.sender()
        if isinstance(editor, widgets.QComboBox):
            depth = editor.itemData(index)
            self.export_item_model.setOverride(COL_EXPORT_DEPTH, depth)
            self.export_item_model.update_column(COL_EXPORT_DEPTH)

    def on_shader_assignment_changed(self, item):
        selected_shaders = self.shader_assignment_model.selected_shaders()
        new_rows = self.export_item_model.update_shader_items(selected_shaders)
        for new_row in new_rows:
            self.export_item_view.expand(new_row.index())

    def on_export_button_pressed(self):
        for_export = self.export_item_model.get_items_for_export()
        
        if len(for_export) == 0:
            return
        
        # Verify file formats are valid for bit depths
        formats_for_bit_depth = {}
        for bit_depth in (mari.Image.DEPTH_BYTE, mari.Image.DEPTH_HALF, mari.Image.DEPTH_FLOAT):
            formats_for_bit_depth[int(bit_depth)] = mari.images.supportedWriteFormats(mari.Image.depthAsInternalFormat(bit_depth))

        depths = mari.exports.depthList()

        override_depth = self.export_item_model.override(COL_EXPORT_DEPTH)
        for shader, export_items in for_export.items():
            for export_item, _ in export_items:
                if override_depth is None:
                    export_item_depth = export_item.depth()
                else:
                    export_item_depth = override_depth
                
                try:
                    power = depths.index(export_item_depth)
                except ValueError:
                    export_depth = None
                else:
                    if power == 0:
                        export_depth = int(export_item.sourceDepth())
                    else:
                        export_depth = 8 * (2**(power-1))
            
                if export_depth is None:
                    print("Export bit depth is invalid")
                    return
                
                export_file_name, export_file_ext = split_ext(export_item.fileTemplate())
                if export_file_ext not in formats_for_bit_depth.get(export_depth, []):
                    print("File format %s not valid for bit depth %s" % (export_file_ext, export_depth))
                    return

        print("Export file formats and bit depths verified.")

        # Apply overrides and file template.
        file_name, file_ext = split_ext(self.default_texture_pattern)
        override_size = self.export_item_model.override(COL_EXPORT_SIZE)
        override_color_space = self.export_item_model.override(COL_EXPORT_COLOR_SPACE)
        for shader, export_items in for_export.items():
            for export_item, _ in export_items:
                export_file_name, export_file_ext = split_ext(export_item.fileTemplate())
                export_file_template = "%s.%s" % (file_name, export_file_ext)

                # Bake point nodes don't have $CHANNEL so replace that with $NODE.
                if isinstance(export_item.sourceNode(), mari.BakePointNode):
                    export_file_template = export_file_template.replace("$CHANNEL", "$NODE")

                export_item.setFileTemplate(export_file_template)

                if override_depth is not None:
                    export_item.setDepth(override_depth)

                if override_size is not None:
                    export_item.setResolution(override_size)

                if override_color_space is not None:
                    export_item.setColorspace(override_color_space)

        print("Export Items updated with file template and overrides.")

        self.saveSettings()
        usd_export_parameters = usd_shade_export.UsdExportParameters()
        try:
            usd_export_parameters.setExportRootPath(self.export_usd_target_dir_widget.path())
            usd_export_parameters.setLookfileTargetFilename(self.look_file_widget.path())
            usd_export_parameters.setAssemblyTargetFilename(self.assembly_file_widget.path())
            usd_export_parameters.setPayloadSourcePath(self.payload_file_widget.path())
            usd_export_parameters.setStageRootPath(self.root_name_widget.text())
        except usd_shade_export.UsdShadeExportError as error:
            mari.app.log("USD Export Error : %s" % error.message)
            mari.utils.message(error.message, error.title, icon=widgets.QMessageBox.Critical, details=error.details)
            return

        usd_material_sources = []

        for shader, export_items in for_export.items():
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

            usd_material_source = usd_shade_export.UsdMaterialSource(shader.name())
            usd_material_source.setBindingLocations(current_geo_version.sourceMeshLocationList())
            usd_shader_source = usd_shade_export.UsdShaderSource(shader)
            for export_item, shader_input_name in export_items:
                usd_shader_source.setInputExportItem(shader_input_name, export_item)
            usd_material_source.setShaderSource(shader.shaderModel().id(), usd_shader_source)
            usd_material_sources.append(usd_material_source)

        try:
            usd_shade_export.exportUsdShadeLook(usd_export_parameters, usd_material_sources)
        except usd_shade_export.UsdShadeExportError as error:
            mari.app.log("USD Export Error : %s" % error.message)
            mari.utils.message(error.message, error.title, icon=widgets.QMessageBox.Critical, details=error.details)
        except Exception as error:
            error_message = "\n".join((str(error), traceback.format_exc()))
            mari.app.log("USD Export Error : %s" % error_message)
            widgets.QMessageBox.critical(self, "Error", error_message)

    def save_paths(self, name, values):
        # Save the current entry with the project.
        project = mari.projects.current()
        if project:
            first_value = values[0] if len(values) > 0 else ""
            if project.hasMetadata(name):
                project.setMetadata(name, first_value)
            elif len(first_value) > 0:
                project.setMetadata(name, first_value)

        # Save the history with the settings.
        settings = mari.Settings()
        settings.setValue("UsdExportDialog/%s" % name, values[:10])
        
    def save_usd_target_dir_paths(self):
        self.save_paths("UsdTargetDirPaths", self.export_usd_target_dir_widget.paths())

    def save_usd_texture_file_paths(self):
        self.save_paths("UsdTexturePaths", self.export_texture_file_widget.paths())

    def save_usd_look_file_paths(self):
        self.save_paths("UsdLookPaths", self.look_file_widget.paths())
        
    def save_usd_assembly_file_paths(self):
        self.save_paths("UsdAssemblyPaths", self.assembly_file_widget.paths())

    def save_usd_payload_file_paths(self):
        self.save_paths("UsdPayloadPaths", self.payload_file_widget.paths())

    def save_root_name(self):
        root_name = self.root_name_widget.text()
        
        name = "UsdRootName"
        
        project = mari.projects.current()
        if project:
            if project.hasMetadata(name):
                project.setMetadata(name, root_name)
            elif len(root_name) > 0:
                project.setMetadata(name, root_name)

        settings = mari.Settings()
        settings.setValue("UsdExportDialog/%s" % name, root_name)

    def onCloseTab(self):
        self.saveSettings()

    def saveSettings(self):
        self.save_usd_target_dir_paths()
        self.save_usd_texture_file_paths()
        self.save_usd_look_file_paths()
        self.save_usd_assembly_file_paths()
        self.save_usd_payload_file_paths()
        self.save_root_name()

def generate_usd_export_widget():
    return USDExportWidget()

if mari.app.isRunning():
    # Register the USD Export tab to the Export Manager
    try:
        mari.system.batch_export_dialog.deregisterCustomTabWidgetCallback("USD Export")
    except ValueError:
        pass
    
    mari.system.batch_export_dialog.registerCustomTabWidgetCallback("USD Export", generate_usd_export_widget)
