""" Mari Export to UsdShade
    coding: utf-8
    Copyright (c) 2017 The Foundry Visionmongers Ltd.  All Rights Reserved.
    Author : Rory Woodford
"""
import datetime
import os
import re

import mari
from pxr import Sdf, Usd, UsdShade

USD_SHADER_INPUT_EXPORT_FUNCTIONS = {}
MARI_TO_USD_SHADER_MAPPING = {}
USD_MATERIAL_TERMINALS = {}


def registerRendererExportPlugin(mari_shader_type_name, usd_shader_id, shader_input_export_func,
    material_terminal_name, material_surface_context
):
    """Registers mappings for renderer specific UsdShade export functions.
    The callback function for exporting a shader input will be called with the following arguments:

        Usd.Stage: Stage to write to
        Usd.Shader: Shader to connect to
        mari.Shader: Source Mari Shader being exported
        mari.ShaderModelInput: The shader input to write
        mari.ExportItem: Export item source for texture maps
        str: Export texture root path

    Args:
        mari_shader_type_name (str): Mari shader type name
        usd_shader_id (str): Shader ID of Usd shader
        shader_input_export_func (function): Callback function to write UsdShade data
        material_terminal_name (str): Name of material terminal
        material_surface_context (str): Name of surface output context
    """
    MARI_TO_USD_SHADER_MAPPING[mari_shader_type_name] = usd_shader_id
    if type(shader_input_export_func).__name__ != "function":
        raise ValueError("No shader input export callback function specified for registerRendererExportPlugin")
    USD_SHADER_INPUT_EXPORT_FUNCTIONS[mari_shader_type_name] = shader_input_export_func
    USD_MATERIAL_TERMINALS[mari_shader_type_name] = (material_surface_context, material_terminal_name)


def writeUsdPreviewSurfaceInput(looks_stage, usd_shader, mari_shader, shader_input_name, export_item,
    export_root_path
):
    """Function to write out the Usd shading nodes for an input to a UsdPreviewSurface shader.

    Args:
        looks_stage (Usd.Stage): Stage to write to
        usd_shader (Usd.Shader): Shader to connect to
        mari_shader (mari.Shader): Source Mari Shader being exported
        shader_input (mari.ShaderModelInput): The shader input to write
        export_item (mari.ExportItem): Export item source for texture maps
        export_root_path (str): Export texture root path
    """
    mari_to_usd_input_map = {
        "diffuseColor": ("diffuseColor", Sdf.ValueTypeNames.Color3f),
        "emissiveColor": ("emissiveColor", Sdf.ValueTypeNames.Color3f),
        "useSpecularWorkflow": ("useSpecularWorkflow", Sdf.ValueTypeNames.Bool),
        "specularColor": ("specularColor", Sdf.ValueTypeNames.Color3f),
        "metallic": ("metallic", Sdf.ValueTypeNames.Float),
        "roughness": ("roughness", Sdf.ValueTypeNames.Float),
        "clearcoat": ("clearcoat", Sdf.ValueTypeNames.Float),
        "clearcoatRoughness": ("clearcoatRoughness", Sdf.ValueTypeNames.Float),
        "opacity": ("opacity", Sdf.ValueTypeNames.Float),
        "opacityThreshold": ("opacityThreshold", Sdf.ValueTypeNames.Float),
        "ior": ("ior", Sdf.ValueTypeNames.Float),
        "Normal": ("normal", Sdf.ValueTypeNames.Normal3f),
        "occlusion": ("occlusion", Sdf.ValueTypeNames.Float),
        "Bump": (None, None),
        "Vector": (None, None),
        "Displacement": ("displacement", Sdf.ValueTypeNames.Float),
    }
    material_sdf_path = usd_shader.GetPath().GetParentPath()

    if export_item is not None:

        # find or define texture coordinate reader
        st_reader_path = material_sdf_path.AppendChild("st_reader")
        st_reader = UsdShade.Shader.Get(looks_stage, st_reader_path)
        if st_reader.GetPath().isEmpty:
            st_reader = UsdShade.Shader.Define(looks_stage, st_reader_path)
            st_reader.CreateIdAttr('UsdPrimvarReader_float2')
            st_reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")

        # Perform the texture export
        if not hasExportItemBeenExported(export_item, export_root_path):
            mari.exports.exportTextures([export_item], export_root_path)

        # Create and connect the texture reading shading node
        usd_shader_input_name, sdf_type = mari_to_usd_input_map[shader_input_name]
        if usd_shader_input_name is not None:
            texture_usd_file_name = re.sub(r"\$UDIM", "<UDIM>", export_item.resolveFileTemplate())
            texture_usd_file_path = os.path.join(export_root_path, texture_usd_file_name)
            texture_sampler_sdf_path = material_sdf_path.AppendChild("{0}Texture".format(shader_input_name))
            texture_sampler = UsdShade.Shader.Define(looks_stage, texture_sampler_sdf_path)
            texture_sampler.CreateIdAttr("UsdUVTexture")
            texture_sampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(st_reader, 'result')
            usd_shader.CreateInput(usd_shader_input_name, sdf_type).ConnectToSource(
                texture_sampler,
                "r" if sdf_type == Sdf.ValueTypeNames.Float else "rgb"
            )
            texture_sampler.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_usd_file_path)


def _sanitize(location_path):
    return location_path.replace(" ", "_")


def _create_new_stage(file_path, root_prim_name):
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
        if export_item.exportEnabled():
            yield shader_model_input, export_item


def exportShaderAsUsdShadeLook(target_dir, looks_filename, assembly_filename, payload_path,
    textures_dir_name, geo_versions, geo_version_to_shader, geo_version_to_export_items, geo_version_to_mesh_locations, export_item_to_shader_input_name, root_name
):
    """Exports a Mari Shader as a UsdShade look file.

    Args:
        target_dir (str): Target location to save Usd files
        looks_filename (str): Name of UsdShade look file
        assembly_filename (str): Name of Usd Assembly file
        payload_path (str): Path to Usd payload
        textures_dir_name (str): Name of textures sub directory
        geo_versions (list of mari.GeoVersion): Geo versions to export
        geo_version_to_shader (dict of mari.GeoVersion : mari.Shader): Shader to export for each geo version exported
        geo_version_to_export_items (dict of mari.GeoVersion : list of mari.ExportItem): Export items to export for each geo version exported
        geo_version_to_mesh_locations (dict of mari.GeoVersion : list of str): Usd locations to assign material to for each geo version exported
        export_item_to_shader_input_name (dict of mari.ExportItem : str): The shader model input name associated with a given export item
        root_name (str): Usd root location
    """
    
    geo_versions_set = set(geo_versions)
    if not geo_versions_set.issubset(set(geo_version_to_shader.keys())):
        raise ValueError("Missing shader associations for geo versions, please ensure each geo version to be exported has an associated shader to export.")
    if not geo_versions_set.issubset(set(geo_version_to_export_items.keys())):
        raise ValueError("Missing export item associations for geo versions, please ensure each geo version to be exported has an associated list of export items to export.")
    if not geo_versions_set.issubset(set(geo_version_to_mesh_locations.keys())):
        raise ValueError("Missing mesh location associations for geo versions, please ensure each geo version to be exported has an associated list of mesh locations to export to.")
    
    export_item_set = set()
    for export_items in geo_version_to_export_items.values():
        export_item_set |= set(export_items)
    
    if not set(export_item_to_shader_input_name.keys()).issubset(export_item_set):
        raise ValueError("Missing shader input name associations for export items, please ensure each export item to be exported has an associated shader input name.")
    
    for geo_version in geo_versions:
        mari_shader = geo_version_to_shader[geo_version]
        shader_model_id = mari_shader.shaderModel().id()
        if shader_model_id not in MARI_TO_USD_SHADER_MAPPING or\
                shader_model_id not in USD_SHADER_INPUT_EXPORT_FUNCTIONS:
            raise ValueError("Shader type {0} has no plugin registered for UsdShade export.".format(shader_model_id))

    sanitized_shader_names = set()
    for geo_version in geo_versions:
        mari_shader = geo_version_to_shader[geo_version]
        sanitized_shader_name = _sanitize(mari_shader.name())
        if sanitized_shader_name in sanitized_shader_names:
            raise ValueError("Conflicting shader name '{0}', please ensure that shaders have unique names to avoid conflicts in the exported Look File.".format(sanitized_shader_name))
        else:
            sanitized_shader_names.add(sanitized_shader_name)

    if os.path.isabs(looks_filename):
        looks_path = looks_filename
    else:
        looks_path = os.path.join(target_dir, looks_filename)
    looks_path = os.path.normpath(looks_path)

    if os.path.exists(looks_path):
        os.remove(looks_path)
    looks_stage = _create_new_stage(looks_path, root_name)
    root_sdf_path = Sdf.Path(root_name)

    # Define shaders for materials
    for geo_version in geo_versions:
        mari_shader = geo_version_to_shader[geo_version]
        shader_model = mari_shader.shaderModel()
        sanitized_shader_name = _sanitize(mari_shader.name())
        material_sdf_path = root_sdf_path.AppendChild(sanitized_shader_name)
        material = UsdShade.Material.Define(looks_stage, material_sdf_path)
        material_shader = UsdShade.Shader.Define(looks_stage, material_sdf_path.AppendChild(sanitized_shader_name))
        shader_model_id = shader_model.id()
        material_shader.SetShaderId(MARI_TO_USD_SHADER_MAPPING[shader_model_id])
        material_surface_context, material_terminal_name = USD_MATERIAL_TERMINALS[shader_model_id]
        if material_surface_context is not None:
            material_output = material.CreateSurfaceOutput(material_surface_context)
        else:
            material_output = material.CreateSurfaceOutput()
        material_output.ConnectToSource(material_shader, material_terminal_name)

        texture_root_path = os.path.normpath(textures_dir_name)

        # for shader_model_input in list(shader_model.inputs().values()):
        for export_item in geo_version_to_export_items[geo_version]:
            shader_input_name = export_item_to_shader_input_name[export_item]
            if export_item and export_item.exportEnabled():
                USD_SHADER_INPUT_EXPORT_FUNCTIONS[shader_model_id](
                    looks_stage,
                    material_shader,
                    mari_shader,
                    shader_input_name,
                    export_item,
                    texture_root_path
                )

        for material_assign_location in geo_version_to_mesh_locations[geo_version]:
            material_assign_sdf_path = Sdf.Path(material_assign_location)
            material_assign_prim = looks_stage.OverridePrim(material_assign_sdf_path)
            UsdShade.MaterialBindingAPI(material_assign_prim).Bind(material)

    looks_stage.GetRootLayer().Save()

    if assembly_filename:
        # setup the assembly stage
        if os.path.isabs(assembly_filename):
            assembly_path = assembly_filename
        else:
            assembly_path = os.path.join(target_dir, assembly_filename)
        assembly_path = os.path.normpath(assembly_path)
        
        assembly_dir = os.path.dirname(assembly_path)

        if os.path.exists(assembly_path):
            os.remove(assembly_path)
        assembly_stage = _create_new_stage(assembly_path, root_name)
        assembly_root_prim = assembly_stage.GetDefaultPrim()

        # add the payload asset
        if not payload_path:
            raise ValueError("Assembly file requested, however no payload asset filename was specified!")
            
        # add the look file as a reference
        try:
            payload_path_rel = os.path.relpath(payload_path, assembly_dir)
        except ValueError:
            payload_path_rel = payload_path # ValueError on Windows if drive differs. Cannot be relative in that case.
            
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
        assembly_stage.GetRootLayer().Save()
        
if mari.app.isRunning():
    # Register the USD Preview Surface exporter.
    registerRendererExportPlugin(
        "USD Preview Surface",
        "UsdPreviewSurface",
        writeUsdPreviewSurfaceInput,
        "surface",
        None
    )