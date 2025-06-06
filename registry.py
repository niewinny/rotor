from bpy.utils import register_class, unregister_class, register_tool, unregister_tool
from . import btypes, preferences, keymap, ops, gizmos, tools
from .icons import load_icons, unload_icons

classes = (
    *btypes.classes,
    *preferences.classes,
    *ops.classes,
    *gizmos.classes,
    *tools.classes,
)


def register():
    load_icons()

    for cls in classes:
        register_class(cls)

    register_tool(tools.mirror.ROTOR_MT_Mirror, group=True, separator=False)
    register_tool(tools.array.ROTOR_MT_Array, after={"rotor.mirror_tool"}, group=False, separator=False)

    btypes.register()
    keymap.register()


def unregister():
    keymap.unregister()

    unregister_tool(tools.mirror.ROTOR_MT_Mirror)
    unregister_tool(tools.array.ROTOR_MT_Array)

    for cls in reversed(classes):
        unregister_class(cls)

    btypes.unregister()
    unload_icons()
