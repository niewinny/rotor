import bpy
from . import ops

class Scene(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.Scene)


class Theme(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.Theme)


classes = [
    *ops.types_classes,
    Scene,
    Theme,
]


def register():
    bpy.types.Scene.rotor = bpy.props.PointerProperty(type=Scene)


def unregister():
    del bpy.types.Scene.rotor
