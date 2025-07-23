import bpy
from . import mirror
from . import set_tool


class Theme(bpy.types.PropertyGroup):
    test: bpy.props.BoolProperty(default=False)

class Scene(bpy.types.PropertyGroup):
    test: bpy.props.BoolProperty(default=False)


types_classes = (
    Scene,
    Theme,
    *mirror.types_classes,
)


classes = (
    *mirror.classes,
    *set_tool.classes,
)
