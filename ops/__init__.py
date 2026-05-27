import bpy
from . import (
    mirror_props,
    mirror_set_axis,
    mirror_add_axis,
    mirror_add_collection,
    mirror_mesh,
    mirror_custom_plane,
    mirror_set_orientation,
    mirror_fallback_tool,
    set_tool,
)


class Theme(bpy.types.PropertyGroup):
    test: bpy.props.BoolProperty(default=False)


class Scene(bpy.types.PropertyGroup):
    test: bpy.props.BoolProperty(default=False)
    last_tool: bpy.props.StringProperty(
        name="Last Tool", description="Last active tool before mirror tool", default=""
    )


types_classes = (
    Scene,
    Theme,
    *mirror_props.types_classes,
)


classes = (
    *mirror_props.classes,
    *mirror_set_axis.classes,
    *mirror_add_axis.classes,
    *mirror_add_collection.classes,
    *mirror_mesh.classes,
    *mirror_custom_plane.classes,
    *mirror_set_orientation.classes,
    *mirror_fallback_tool.classes,
    *set_tool.classes,
)
