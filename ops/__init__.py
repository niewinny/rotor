import bpy
from . import mirror
from . import array
from . import set_tool


class Theme(bpy.types.PropertyGroup):
    test: bpy.props.BoolProperty(default=False)

class Scene(bpy.types.PropertyGroup):
    test: bpy.props.BoolProperty(default=False)


types_classes = (
    Scene,
    Theme,
)


classes = (
    *mirror.classes,
    *array.classes,
    *set_tool.classes,
)
