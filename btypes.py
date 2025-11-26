import bpy
from . import ops
from . import tools


class Tools(bpy.types.PropertyGroup):
    mirror: bpy.props.PointerProperty(type=tools.props.Mirror)
    # array tool now uses geometry nodes directly, no need for property group


class Scene(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.Scene)


class ThemeAxis(bpy.types.PropertyGroup):
    x: bpy.props.FloatVectorProperty(
        name="Axis X",
        description="X axis color",
        default=(1.0, 0.2, 0.322, 0.8),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    y: bpy.props.FloatVectorProperty(
        name="Y",
        description="Y axis colo",
        default=(0.545, 0.863, 0.0, 0.8),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    z: bpy.props.FloatVectorProperty(
        name="Z",
        description="Z axis colo",
        default=(0.157, 0.564, 1.0, 0.8),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    g: bpy.props.FloatVectorProperty(
        name="G",
        description="gray",
        default=(0.12, 0.12, 0.12, 0.8),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )
    n: bpy.props.FloatVectorProperty(
        name="N",
        description="yellow",
        default=(0.85, 0.75, 0.0, 0.8),
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
    )


class Theme(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.Theme)
    axis: bpy.props.PointerProperty(type=ThemeAxis)


classes = [
    *ops.types_classes,
    *tools.types_classes,
    Tools,
    Scene,
    ThemeAxis,
    Theme,
]


def register():
    bpy.types.Scene.rotor = bpy.props.PointerProperty(type=Scene)


def unregister():
    del bpy.types.Scene.rotor
