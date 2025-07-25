import bpy
from . import mirror
from . import set_tool


class Theme(bpy.types.PropertyGroup):
    test: bpy.props.BoolProperty(default=False)

class Scene(bpy.types.PropertyGroup):
    test: bpy.props.BoolProperty(default=False)
    last_tool: bpy.props.StringProperty(
        name="Last Tool",
        description="Last active tool before mirror tool",
        default="")


types_classes = (
    Scene,
    Theme,
    *mirror.types_classes,
)


classes = (
    *mirror.classes,
    *set_tool.classes,
)
