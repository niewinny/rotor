import bpy


class Theme(bpy.types.PropertyGroup):
    test: bpy.props.BoolProperty(default=False)

class Scene(bpy.types.PropertyGroup):
    test: bpy.props.BoolProperty(default=False)


types_classes = (
    Scene,
    Theme,
)


classes = (
)
