from bpy.utils import register_class, unregister_class, register_tool, unregister_tool
from . import btypes, preferences, keymap, ops, tools
from .icons import load_icons, unload_icons

classes = (
    *btypes.classes,
    *preferences.classes,
    *ops.classes,
)


def register():
    load_icons()

    for cls in classes:
        register_class(cls)

    register_tool(tools.rotor.ROTOR_MT_Mirror, group=False, separator=True)

    btypes.register()
    # keymap.register() 


def unregister():
    # keymap.unregister()

    unregister_tool(tools.rotor.ROTOR_MT_Mirror)

    for cls in reversed(classes):
        unregister_class(cls)

    btypes.unregister()
    unload_icons()
