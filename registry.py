from bpy.utils import register_class, unregister_class
from . import btypes, preferences, keymap, ops
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

    btypes.register()
    # keymap.register()


def unregister():
    # keymap.unregister()

    for cls in reversed(classes):
        unregister_class(cls)

    btypes.unregister()
    unload_icons()
