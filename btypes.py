import bpy
from . import ops
from . import tools


class Tools(bpy.types.PropertyGroup):
    mirror: bpy.props.PointerProperty(type=tools.rotor.Mirror)


class Scene(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.Scene)


class Theme(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.Theme)


classes = [
    *ops.types_classes,
    *tools.types_classes,
    Tools,
    Scene,
    Theme,
]


def register():
    bpy.types.Scene.rotor = bpy.props.PointerProperty(type=Scene)


def unregister():
    del bpy.types.Scene.rotor
