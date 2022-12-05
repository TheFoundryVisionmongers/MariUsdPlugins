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

import datetime
import os

import mari
from pxr import Sdf, Usd, UsdShade, Tf, UsdGeom

USD_SHADER_EXPORT_FUNCTIONS = {}
MARI_TO_USD_SHADER_MAPPING = {}
USD_MATERIAL_TERMINALS = {}
USD_FUNCTION_CALLBACKS = {}

CALLBACK_NAME_SETTINGS_WIDGET = "SettingsWidget"
CALLBACK_NAME_SETUP_EXPORT_ITEM = "SetupExportItem"
CALLBACK_NAME_EXPORT_EXPORT_ITEM = "ExportExportItem"

class UsdShadeExportError(Exception):
    """Custom Exception for known errors hit when exporting to UsdShade
    """

    def __init__(self, title, message, details=None):
        super(UsdShadeExportError, self).__init__()

        self.title = title
        self.message = message
        self.details = details

    def __repr__(self):
        return "UsdShadeExportError({0}:{1})".format(self.title, self.message)

    def __str__(self):
        return "{0}:{1}".format(self.title, self.message)


class UsdShaderSource(object):
    """Container class for all Mari Entity instances required to author a UsdShade network for a
    specific render target context.
    """
    def __init__(self, source_shader):
        super(UsdShaderSource, self).__init__()

        self._source_shader = source_shader
        self._export_items = {}
        self._uv_set_name = "st"

    def to_dict(self):
        """ Returns the contents of the class instance as a dictionary.

        Returns:
            dict: Dictionary representation of data
        """
        usd_shader_source_data = {
            "source_shader": self._source_shader,
            "export_items": {},
        }
        for shader_input_name, export_item in self._export_items.items():
            usd_shader_source_data["export_items"][shader_input_name] = export_item

        return usd_shader_source_data

    @classmethod
    def from_dict(cls, usd_shader_source_data):
        """Generates a UsdShaderSource instance from the given data dictionary.

        The dictionary needs to match the following structure::
            {
                "source_shader": mari.Shader instance
                "export_items": { # Dict of stream name keys and mari.ExportItem instance values
                    "BaseColor": mari.ExportItem instance,
                },
            }

        Args:
            usd_shader_source_data (dict) : UsdShaderSource data dictionary

        Returns:
            UsdShaderSource: New UsdShaderSource instance
        """
        if "source_shader" not in usd_shader_source_data:
            raise ValueError("source_shader key not in usd_shader_source_data")
        usd_shader_source = cls(usd_shader_source_data["source_shader"])
        for shader_input_name, export_item in usd_shader_source_data.get("export_items", {}).items():
            usd_shader_source.setInputExportItem(shader_input_name, export_item)

        return usd_shader_source

    def shaderModel(self):
        """Convenience function to return Shader Model of source Shader

        Returns:
            mari.ShaderModel: Shader Model of source Shader
        """
        return self._source_shader.shaderModel()

    def sourceShader(self):
        """ Returns the contained source shader.

        Returns:
            mari.Shader: Source shader
        """
        return self._source_shader

    def setInputExportItem(self, shader_input_name, export_item):
        """ Sets the export item for the specified shader input.

        Args:
            shader_input_name (str): Shader input name.
            export_item (mari.ExportItem): Export Item

        Raises:
            ValueError: When the shader input name is not from the associated shader model
        """
        if shader_input_name not in self.shaderModel().inputNames():
            raise ValueError(
                "Given input name ({0}) is not a member of the represented shader's model ({1})".format(
                    shader_input_name,
                    self.shaderModel().id()
                )
            )
        self._export_items[shader_input_name] = export_item

    def getInputExportItem(self, shader_input_name):
        """ Returns the export item for the specified shader input.

        Args:
            shader_input_name (str): Shader input name.

        Returns:
            mari.ExportItem: Export Item source
        """
        return self._export_items.get(shader_input_name)

    def uvSetName(self):
        """ Returns the UV set name.

        Returns:
            str. UV set name
        """
        return self._uv_set_name

    def setUvSetName(self, uv_set_name):
        """ Sets the container's UV set name.

        Args:
            uv_set_name (str): Material binding locations
        """
        self._uv_set_name = uv_set_name


class UsdMaterialSource(object):
    """Container class for all Mari Entity instances required to author a UsdShade Look
    """
    def __init__(self, name):
        super(UsdMaterialSource, self).__init__()

        self._name = name
        self._shader_sources = {}
        self._binding_locations = []
        self._selection_groups = []

    def to_dict(self):
        """ Returns the contents of the class instance as a dictionary.

        Returns:
            dict: Dictionary representation of data
        """
        usd_material_source_data = {
            "name": self._name,
            "shader_sources": {},
            "binding_locations": list(self._binding_locations),
            "selection_groups": list(self._selection_groups),
        }
        for mari_shader_type_name, usd_shader_source in self._shader_sources.items():
            usd_material_source_data["shader_sources"][mari_shader_type_name] = usd_shader_source.to_dict()

        return usd_material_source_data

    @classmethod
    def from_dict(cls, usd_material_source_data):
        """Generates a UsdMaterialSource instance from the given data dictionary.

        The dictionary needs to match the following structure::
            {
                "name": str # Name of USD Material
                "binding_locations": list # Mesh locations to apply material bindings
                "selection_groups": list # UUID strings of selection groups
                "shader_sources": { # Dict of Mari shader type keys and UsdShaderSource dict values
                    "UsdPreviewSurface": {
                        "source_shader": mari.Shader instance
                        "export_items": { # Dict of stream name keys and mari.ExportItem instance values
                            "BaseColor": mari.ExportItem instance,
                        },
                    }
                },
            }

        Args:
            usd_material_source_data (dict) : UsdMaterialSource data dictionary

        Returns:
            UsdMaterialSource: New UsdMaterialSource instance
        """
        if "name" not in usd_material_source_data:
            raise ValueError("name key not in usd_material_source_data")
        usd_material_source = cls(usd_material_source_data["name"])
        usd_material_source.setBindingLocations(usd_material_source_data.get("binding_locations", []))
        usd_material_source.setSelectionGroups(usd_material_source_data.get("selection_groups", []))
        for mari_shader_type_name, shader_source_data in usd_material_source_data.get("shader_sources", {}).items():
            usd_material_source.setShaderSource(mari_shader_type_name, UsdShaderSource.from_dict(shader_source_data))

        return usd_material_source

    def name(self):
        """ Returns name of Usd Material

        Returns:
            str. Name of Usd Material
        """
        return self._name

    def shaderSource(self, mari_shader_type_name):
        """ Returns the source Mari Shader of the specified shader type.
        Args:
            mari_shader_type_name (str): Mari Shader type name.

        Returns:
            UsdShaderSource: Mari shader source container
        """
        return self._shader_sources.get(mari_shader_type_name)

    def setShaderSource(self, mari_shader_type_name, shader_source):
        """ Populates the given shader source container into the specified shader type

        Args:
            mari_shader_type_name (str): Mari Shader type name.
            shader_source (UsdShaderSource): Shader source container
        """
        if not isinstance(shader_source, UsdShaderSource):
            raise ValueError(
                "Only UsdShaderSource instances can be set as the shader source of a UsdMaterialSource instance. "
                "Instance of %s given instead." % type(shader_source)
            )
        self._shader_sources[mari_shader_type_name] = shader_source

    def shaderSourceList(self):
        """ Returns the list of contained Usd Shader source containers

        Returns:
            list of UsdShaderSource: Usd Shader source containers
        """
        return list(self._shader_sources.values())

    def bindingLocations(self):
        """ Returns the material binding locations

        Returns:
            list of str. Material binding locations
        """
        return self._binding_locations

    def setBindingLocations(self, binding_locations):
        """ Sets the container's material binding locations.

        Args:
            binding_locations (list of str): Material binding locations
        """
        self._binding_locations = binding_locations

    def selectionGroups(self):
        """ Returns the UUID strings of selection groups.

        Returns:
            list of str. UUI strings of selection groups.
        """
        return self._selection_groups

    def setSelectionGroups(self, selection_groups):
        """ Sets the UUID strings of selection groups.

        Args:
            selection_groups (list of str): UUID strings of selection groups.
        """
        self._selection_groups = selection_groups


class UsdExportParameters(object):
    """Container class for all parameters necessary for exporting Mari project data to UsdShade Looks.
    """

    def __init__(self):
        super(UsdExportParameters, self).__init__()

        self._export_root_path = ""
        self._lookfile_target_filename = "Lookfile.usda"
        self._assembly_target_filename = ""
        self._payload_source_path = ""
        self._stage_root_path = "/root"
        self._export_overrides = {}

    def setExportRootPath(self, export_root_path):
        """ Sets the export root path location

        Args:
            export_root_path (str): Export root path

        Returns:
            bool. Export root path has changed

        Raises:
            UsdShadeExportError: When the specified path does not exist.
        """
        if not os.path.exists(export_root_path):
            raise UsdShadeExportError(
                "Export Root Path Does Not Exist",
                "The specified export root path does not exist:\n\n    {0}".format(export_root_path)
            )
        if export_root_path != self._export_root_path:
            self._export_root_path = export_root_path
            return True
        return False

    def exportRootPath(self):
        """ Returns the set export root path

        Returns:
            str. Export root path
        """
        return os.path.normpath(self._export_root_path)

    def setExportOverrides(self, export_overrides):
        """ Sets the export overrides mapping for mari.exports.exportTextures()

        Args:
            export_overrides (dict): The map of export settings

        Returns:
            bool. Export override map has changed
        """

        if export_overrides != self._export_overrides:
            self._export_overrides = export_overrides
            return True
        return False

    def exportOverrides(self):
        """ Returns the map of export overrides

        Returns:
            dict. Export overrides
        """
        return self._export_overrides

    def setLookfileTargetFilename(self, lookfile_target_filename):
        """ Sets the filename for the Lookfile export target

        Args:
            lookfile_target_filename (str): Lookfile target filename

        Returns:
            bool. Lookfile export target path has changed

        Raises:
            UsdShadeExportError: Target path does not exist
        """
        # Is target just a filename
        if os.path.basename(lookfile_target_filename) == lookfile_target_filename:
            if not self._export_root_path:
                raise UsdShadeExportError(
                    "Export Root Path Undefined",
                    "The export root path has not yet been defined"
                )
            lookfile_target_filename = os.path.normpath(os.path.join(self._export_root_path, lookfile_target_filename))

        # Ensure directory exists
        if not os.path.exists(os.path.dirname(lookfile_target_filename)):
            raise UsdShadeExportError(
                "Target Directory does not Exist",
                "{0}\n\n    {1} does not exist".format(
                    "The given directory for the Lookfile file to be written to does not exist.",
                    os.path.dirname(lookfile_target_filename)
                )
            )
        if self._lookfile_target_filename != lookfile_target_filename:
            self._lookfile_target_filename = lookfile_target_filename
            return True
        else:
            return False

    def lookfileTargetFilename(self):
        """ Returns the set Lookfile target filename

        Returns:
            str. Lookfile target filename
        """
        return self._lookfile_target_filename

    def lookfileTargetPath(self):
        """ Returns the set Lookfile target path

        Returns:
            str. Lookfile target path
        """
        if os.path.isabs(self._lookfile_target_filename):
            looks_path = self._lookfile_target_filename
        else:
            looks_path = os.path.join(self._export_root_path, self._lookfile_target_filename)
        return os.path.normpath(looks_path)

    def setAssemblyTargetFilename(self, assembly_target_filename):
        """ Sets the filename for the Assembly export target

        Args:
            assembly_target_filename (str): Assembly target filename

        Returns:
            bool. Assembly export target path has changed

        Raises:
            UsdShadeExportError: Target path does not exist
        """
        # Is target just a filename
        if os.path.basename(assembly_target_filename) == assembly_target_filename:
            if not self._export_root_path:
                raise UsdShadeExportError(
                    "Export Root Path Undefined",
                    "The export root path has not yet been defined"
                )
            assembly_target_filename = os.path.normpath(os.path.join(self._export_root_path, assembly_target_filename))

        if not os.path.exists(os.path.dirname(assembly_target_filename)):
            raise UsdShadeExportError(
                "Target Directory does not Exist",
                "{0}\n\n    {1} does not exist".format(
                    "The given directory for the assembly file to be written to does not exist.",
                    os.path.dirname(assembly_target_filename)
                )
            )
        if self._assembly_target_filename != assembly_target_filename:
            self._assembly_target_filename = assembly_target_filename
            return True
        else:
            return False

    def assemblyTargetFilename(self):
        """ Returns the set Assembly target filename

        Returns:
            str. Assembly target filename
        """
        return self._assembly_target_filename

    def assemblyTargetPath(self):
        """ Returns the set Assembly target path

        Returns:
            str. Assembly target path

        Raises:
            ValueError. When assembly target filename is not set
        """
        if not self._assembly_target_filename:
            raise ValueError("Cannot resolve absolute path for assembly target as filename is empty")
        if os.path.isabs(self._assembly_target_filename):
            assembly_path = self._assembly_target_filename
        else:
            assembly_path = os.path.join(self._export_root_path, self._assembly_target_filename)
        return os.path.normpath(assembly_path)

    def setPayloadSourcePath(self, payload_source_path):
        """ Sets the path of the payload file

        Args:
            payload_source_path (str): Payload source path

        Returns:
            bool. Assembly export target path has changed

        Raises:
            UsdShadeExportError: Target path does not exist
        """
        if not os.path.isabs(payload_source_path):
            if not self._export_root_path:
                raise UsdShadeExportError(
                    "Export Root Path Undefined",
                    "The export root path has not yet been defined"
                )
            payload_source_path = os.path.normpath(os.path.join(self._export_root_path, payload_source_path))
        if not os.path.exists(payload_source_path):
            raise UsdShadeExportError(
                "Payload File does not Exist",
                "{0}\n\n    {1} does not exist".format(
                    "The given payload USD file does not exist.",
                    payload_source_path
                )
            )
        if self._payload_source_path != payload_source_path:
            self._payload_source_path = payload_source_path
            return True
        else:
            return False

    def payloadSourcePath(self):
        """ Returns the set payload source path

        Returns:
            str. Payload source path
        """
        return self._payload_source_path

    def setStageRootPath(self, stage_root_path):
        """ Validates and sets the root path of the Stage to be created

        Args:
            stage_root_path (str): Stage root path

        Returns:
            bool. Stage root path has changed

        Raises:
            UsdShadeExportError: Various reasons for the root path to be invalid
        """
        if not stage_root_path:
                raise UsdShadeExportError(
                    "Empty Root Name",
                    "No root name has been specified for the exporting USD stage."
                )
        if not stage_root_path.startswith("/"):
                raise UsdShadeExportError(
                    "Invalid Root Name",
                    "The given path is not absolute.\nPlease ensure it starts with a '/'"
                )
        if stage_root_path.endswith("/"):
                raise UsdShadeExportError(
                    "Invalid Root Name",
                    "The given root path has a trailing `/`"
                )
        if self._stage_root_path != stage_root_path:
            self._stage_root_path = stage_root_path
            return True
        else:
            return False

    def stageRootPath(self):
        """ Returns the set stage root path name

        Returns:
            str. Stage root path name
        """
        return self._stage_root_path

    def stageSdfRootPath(self):
        """ Returns the set payload source path

        Returns:
            Sdf.Path. Stage root path
        """
        return Sdf.Path(self._stage_root_path)


def registerRendererExportPlugin(mari_shader_type_name, usd_shader_id, shader_input_export_func,
    material_terminal_name, material_surface_context, function_callbacks=None
):
    """Registers mappings for renderer specific UsdShade export functions.
    The callback function for exporting a shader input will be called with the following arguments:

        Usd.Stage: Stage to write to
        Usd.Shader: Shader to connect to
        UsdExportParameters: Container for export parameters
        UsdShaderSource: Container for source Shader and Export Items to export

    Args:
        mari_shader_type_name (str): Mari shader type name
        usd_shader_id (str): Shader ID of Usd shader
        shader_input_export_func (function): Callback function to write UsdShade data
        material_terminal_name (str): Name of material terminal
        material_surface_context (str): Name of surface output context
        function_callbacks (dict{str: function}): Optional function table
        
    Callback Functions:
        A named function table in the format of a dictionary ({name: function}) for shader specific functionality
        Not all functions must be present
        Names:
            CALLBACK_NAME_SETTINGS_WIDGET: Return a QWidget to display in the settings dialog. Takes no parameters
            CALLBACK_NAME_SETUP_EXPORT_ITEM: Called just after an export item is created. Takes one parameter of type mari.ExportItem
            CALLBACK_NAME_EXPORT_EXPORT_ITEM: Called just before an export item is exported. Takes one parameter of type mari.ExportItem
    """
    MARI_TO_USD_SHADER_MAPPING[mari_shader_type_name] = usd_shader_id
    if type(shader_input_export_func).__name__ != "function":
        raise ValueError("No shader input export callback function specified for registerRendererExportPlugin")
    USD_SHADER_EXPORT_FUNCTIONS[mari_shader_type_name] = shader_input_export_func
    USD_MATERIAL_TERMINALS[mari_shader_type_name] = (material_surface_context, Tf.MakeValidIdentifier(material_terminal_name))
    
    if function_callbacks is None:
        pass
    elif isinstance(function_callbacks, dict):
        for callback_name in function_callbacks:
            callback_func = function_callbacks[callback_name]
            if callback_func is not None and type(callback_func).__name__ != "function":
                raise ValueError("Supplied value for callback '%s' is not a function." % callback_name)
        
        USD_FUNCTION_CALLBACKS[mari_shader_type_name] = function_callbacks
    else:
        raise ValueError("Function callbacks must be a dictionary")

def shaderIDsWithFunctionCallbacks(callback_name=None):
    if callback_name is None:
        return USD_FUNCTION_CALLBACKS.keys()

    shader_ids = []
    for mari_shader_model_id in USD_FUNCTION_CALLBACKS.keys():
        if USD_FUNCTION_CALLBACKS[mari_shader_model_id].get(callback_name, None) is not None:
            shader_ids.append(mari_shader_model_id)

    return shader_ids

def functionCallbacksForShader(mari_shader_model_id):
    return USD_FUNCTION_CALLBACKS.get(mari_shader_model_id, {})

def functionCallbackForShader(mari_shader_model_id, callback_name):
    return USD_FUNCTION_CALLBACKS.get(mari_shader_model_id, {}).get(callback_name, None)

def _sanitize(location_path):
    return location_path.replace(" ", "_")


def _debuglog(message):
    """Wrap message in a USD Export specific log message"""
    mari.app.log("USD Export: %s" % message)


def _create_new_stage(file_path, root_prim_name):
    _debuglog("Creating Stage at %s" % file_path)
    stage = Usd.Stage.CreateNew(file_path)
    now = datetime.datetime.now()
    stage.SetMetadata(
        "comment",
        "Generated by Mari on {}".format(now.strftime("%d/%b/%Y %H:%M:%S"))
    )
    root_prim = stage.DefinePrim(root_prim_name)
    stage.SetDefaultPrim(root_prim)
    return stage


def hasExportItemBeenExported(export_item, export_root_path):
    """Checks whether any of the export item files have been exported to the specified export path.

    Args:
        export_item (mari.ExportItem): Export Item to inspect
        export_root_path (str): Path to export items to

    Returns:
        bool: Result of check
    """
    for export_path in export_item.resolveExportFilePaths(export_root_path):
        if os.path.exists(export_path):
            return True

    return False


def getNodeOutputNameConnectedToNodeInputPort(src_node, dst_target_node, dst_target_port_name):
    """Returns the output port name that is connecting the source node to the destination node and
    input port.

    Args:
        src_node (mari.Node): Source node
        dst_target_node (mari.Node): Destination node
        dst_target_port_name (str): Name of destination node's input port

    Returns:
        str: Name of output port
    """
    for output_port_name in src_node.outputPortNames():
        for target_node, target_port_name in src_node.outputNodes(output_port_name):
            if target_node == dst_target_node and target_port_name == dst_target_port_name:
                return output_port_name
    raise ValueError(
        "Node %s has no connection to destination node port %s.%s" % (
            src_node.name(),
            dst_target_node.name(),
            dst_target_port_name
        )
    )


def getExportItemForShaderInput(mari_shader, shader_model_input):
    """Returns the Export Item for the specified Mari shader and input if one can be found
    directly connected to the Shader

    Args:
        mari_shader (mari.Shader): Shader to walk upstream from
        shader_model_input (mari.ShaderModelInput): Input to walk from

    Returns:
        mari.ExportItem: Matching export item for the Shader Input
    """
    mari_shader_node = mari_shader.shaderNode()
    mari_geo_entity = mari_shader_node.parentNodeGraph().parentGeoEntity()
    shader_input_name = shader_model_input.name()
    shader_input_node, shader_input_node_output_port = mari_shader_node.inputConnection(shader_input_name)
    if shader_input_node is None:
        return

    if isinstance(shader_input_node, mari.GroupNode):
        output_node = shader_input_node.groupOutputNode(shader_input_node_output_port)
        if output_node:
            shader_input_node = output_node.inputNode("Input")
        else:
            shader_input_node = None

    if isinstance(shader_input_node, (mari.ChannelNode, mari.BakePointNode)):
        for export_item in mari.exports.exportItemList(mari_geo_entity):
            if export_item.sourceNode() == shader_input_node:
                return export_item


def getInputExportItems(mari_shader):
    """Yields a tuple of the shader model input and source image set based input node of the
    specified Mari shader.

    Args:
        mari_shader (mari.Shader): Shader to extract source nodes from
    Returns:
        (mari.ShaderModelInput, mari.Node): Shader model input and source image set based node pair
    """
    mari_shader_model = mari_shader.shaderModel()
    for shader_model_input in list(mari_shader_model.inputs().values()):
        export_item = getExportItemForShaderInput(mari_shader, shader_model_input)
        if export_item and export_item.exportEnabled():
            yield shader_model_input, export_item


def exportUsdShadeLook(usd_export_parameters, usd_material_sources):
    """Exports a Mari Shader as a UsdShade look file.

    Args:
        usd_export_parameters (UsdExportParameters): Container of export parameters
        usd_material_sources (list of UsdMaterialSource): List of source Mari entity containers to export from
    """
    sanitized_shader_names = set()
    for usd_material_source in usd_material_sources:
        for usd_shader_source in usd_material_source.shaderSourceList():
            # Check for duplicate shader names
            sanitized_shader_name = _sanitize(usd_shader_source.sourceShader().name())
            if sanitized_shader_name in sanitized_shader_names:
                raise UsdShadeExportError(
                    "Shader Name Conflict",
                    " ".join((
                        "Conflicting shader name '{0}',".format(sanitized_shader_name),
                        "please ensure that shaders have unique names to avoid conflicts in the exported Look File."
                    ))
                )
            else:
                sanitized_shader_names.add(sanitized_shader_name)

            # Check for unregistered shader types
            shader_model_id = usd_shader_source.shaderModel().id()
            if shader_model_id not in MARI_TO_USD_SHADER_MAPPING or\
                    shader_model_id not in USD_SHADER_EXPORT_FUNCTIONS:
                raise UsdShadeExportError(
                    "No Exporter for Shader Type",
                    "Shader type {0} has no plugin registered for UsdShade export.".format(shader_model_id)
                )

    looks_path = usd_export_parameters.lookfileTargetPath()
    if os.path.exists(looks_path):
        os.remove(looks_path)

    looks_stage = _create_new_stage(looks_path, usd_export_parameters.stageRootPath())
    root_sdf_path = usd_export_parameters.stageSdfRootPath()

    # Pre cache the map from selection group UUID to instance
    selection_group_uuid_to_instance_map = {}
    for selection_group in mari.selection_groups.list():
        selection_group_uuid_to_instance_map[selection_group.uuid()] = selection_group

    for usd_material_source in usd_material_sources:
        # Define shader for material
        _debuglog("Defining material for %s" % usd_material_source.name())
        material_sdf_path = root_sdf_path.AppendChild(_sanitize(usd_material_source.name()))
        material = UsdShade.Material.Define(looks_stage, material_sdf_path)
        for usd_shader_source in usd_material_source.shaderSourceList():
            mari_shader = usd_shader_source.sourceShader()
            shader_model = mari_shader.shaderModel()
            material_shader = UsdShade.Shader.Define(looks_stage, material_sdf_path.AppendChild(_sanitize(mari_shader.name())))
            material_shader.SetShaderId(MARI_TO_USD_SHADER_MAPPING[shader_model.id()])
            material_surface_context, material_terminal_token = USD_MATERIAL_TERMINALS[shader_model.id()]
            if material_surface_context is not None:
                material_output = material.CreateSurfaceOutput(material_surface_context)
            else:
                material_output = material.CreateSurfaceOutput()
            material_output.ConnectToSource(material_shader.ConnectableAPI(), material_terminal_token)

            USD_SHADER_EXPORT_FUNCTIONS[shader_model.id()](
                looks_stage,
                material_shader,
                usd_export_parameters,
                usd_shader_source
            )

        # mesh_location_to_face_count stores the map of mesh_location to the number of faces. The subset creation code later checks
        # whether the selected faces is actually the entier set of faces for the mesh_location using this map.
        # e.g. If the selection set is "0-99" and the mesh_location has 100 faces, then there is no point of creating a subset.
        mesh_location_to_face_count = {}

        mesh_location_to_face_index_range = {}
        for selection_group_uuid in usd_material_source.selectionGroups():
            if not selection_group_uuid in selection_group_uuid_to_instance_map:
                continue

            selection_group = selection_group_uuid_to_instance_map[selection_group_uuid]

            for key, value in selection_group.meshLocationToFaceSelectionIndexRangeListMap().items():
                if key in mesh_location_to_face_index_range:
                    mesh_location_to_face_index_range[key] = mesh_location_to_face_index_range[key] | set(value.indexList())
                else:
                    mesh_location_to_face_index_range[key] = set(value.indexList())

            for geo_version in selection_group.geoVersionList():
                for key, value in geo_version.meshLocationToFaceCountMap().items():
                    if key in mesh_location_to_face_count:
                        _debuglog("Warning: Mesh location is not unique : %s" % key)
                    else:
                        mesh_location_to_face_count[key] = value

        use_selecgion_group_assignment = len(mesh_location_to_face_index_range) > 0

        _debuglog("Assigning locations to material %s" % usd_material_source.name())
        for material_assign_location in usd_material_source.bindingLocations():
            if use_selecgion_group_assignment and not material_assign_location in mesh_location_to_face_index_range:
                continue

            material_assign_sdf_path = Sdf.Path(material_assign_location)
            material_assign_prim = looks_stage.OverridePrim(material_assign_sdf_path)

            bind_target = material_assign_prim

            if use_selecgion_group_assignment:
                faces = list(mesh_location_to_face_index_range[material_assign_location])
                faces.sort()
                if len(faces) == mesh_location_to_face_count[material_assign_location] and faces[0] == 0 and faces[-1] == mesh_location_to_face_count[material_assign_location]-1:
                    # faces contain the full set of faces for the mesh location. There is no need for subset material assignment. e.g faces = [0-10], where the count is 11
                    pass
                else:
                    subset = UsdGeom.Subset.Define(looks_stage, material_assign_prim.GetPath().AppendChild("materialBindSubset_"+usd_material_source.name()))
                    subset.CreateFamilyNameAttr("materialBind")
                    subset.CreateIndicesAttr(faces)
                    bind_target = subset
            try:
                UsdShade.MaterialBindingAPI(bind_target).Bind(material)
            except Tf.ErrorException:
                _debuglog("Warning: Unable to bind material to %s" % material_assign_prim)

    _debuglog("Saving Lookfile stage to disk: %s" % looks_path)
    looks_stage.GetRootLayer().Save()

    if usd_export_parameters.assemblyTargetFilename():
        # setup the assembly stage
        assembly_path = usd_export_parameters.assemblyTargetPath()
        _debuglog("About to write Assembly file: %s" % assembly_path)
        assembly_dir = os.path.dirname(assembly_path)
        if os.path.exists(assembly_path):
            os.remove(assembly_path)
        assembly_stage = _create_new_stage(assembly_path, usd_export_parameters.stageRootPath())
        assembly_root_prim = assembly_stage.GetDefaultPrim()

        # add the payload asset
        if not usd_export_parameters.payloadSourcePath():
            raise UsdShadeExportError(
                "Missing Payload File",
                "Assembly file requested, however no payload asset filename was specified."
            )

        # add the look file as a reference
        try:
            payload_path_rel = os.path.relpath(usd_export_parameters.payloadSourcePath(), assembly_dir)
        except ValueError:
            payload_path_rel = usd_export_parameters.payloadSourcePath() # ValueError on Windows if drive differs. Cannot be relative in that case.

        payload = Sdf.Payload(payload_path_rel)
        assembly_root_prim.GetPayloads().AddPayload(
            payload,
            position=Usd.ListPositionBackOfAppendList
        )

        # add the look file as a reference
        try:
            looks_path_rel = os.path.relpath(looks_path, assembly_dir)
        except ValueError:
            looks_path_rel = looks_path # ValueError on Windows if drive differs. Cannot be relative in that case.

        assembly_root_prim.GetReferences().AddReference(
            looks_path_rel,
            # looks_path,
            position=Usd.ListPositionBackOfAppendList
        )
        _debuglog("Saving assembly stage to disk: %s" % assembly_path)
        assembly_stage.GetRootLayer().Save()

def payloadDefaultRootName(payload_file_path):
    """Returns the default root name of the given payload file path.

    Args:
        payload_file_path (str): File path of the payload file
    Returns:
        (str): The default root name of the given payload file path.
    """
    if os.path.exists(payload_file_path):
        try:
            payload_stage = Usd.Stage.Open(payload_file_path)
            payload_default_prim = payload_stage.GetDefaultPrim()
            payload_root_name = str(payload_default_prim.GetPath())
            return payload_root_name
        except Exception as e:
            _debuglog("Warning: The Payload file is not a USD file : %s" % str(e))
    geo_entity = mari.geo.current()
    if geo_entity and geo_entity.hasMetadata("StagePrimPath"):
        return geo_entity.metadata("StagePrimPath")
    return "/root"

def colorComponentForType(sdf_type):
    if sdf_type in (Sdf.ValueTypeNames.Float, Sdf.ValueTypeNames.Int, Sdf.ValueTypeNames.Bool):
        return "r"

    return "rgb"

def isValueDefault(input_value, default_color):
    if isinstance(input_value, mari.Color):
        if input_value.rgb() != default_color.rgb():
            return False
    elif isinstance(input_value, mari.VectorN):
        input_value_components = input_value.asTuple()
        default_color_components = default_color.rgba()
        for component in range(input_value.size()):
            if input_value_components[component] != default_color_components[component]:
                return False
    elif isinstance(input_value, float):
        if input_value != default_color.r():
            return False
    elif isinstance(input_value, int):
        if input_value != int(default_color.r()):
            return False
    elif isinstance(input_value, bool):
        if input_value != bool(default_color.r()):
            return False

    return True

def valueAsShaderParameter(input_value, sdf_type):
    if sdf_type == Sdf.ValueTypeNames.Color3f:
        return sdf_type.type.pythonClass(input_value.rgb())
    elif sdf_type == Sdf.ValueTypeNames.Vector3f:
        if isinstance(input_value, mari.Mari.Color):
            return sdf_type.type.pythonClass(input_value.rgb())
        elif isinstance(input_value, mari.Mari.VectorN):
            return sdf_type.type.pythonClass(input_value.asTuple())
    elif sdf_type in (Sdf.ValueTypeNames.Float, Sdf.ValueTypeNames.Int, Sdf.ValueTypeNames.Bool):
        return input_value

