import bpy
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

    has_blockout = False
    
    addon_prefs = bpy.context.preferences.addons
    for addon_name in addon_prefs.keys():
        if 'blockout' in addon_name.lower() or 'bout' in addon_name.lower():
            has_blockout = True
    
    # Register with appropriate settings
    if has_blockout:
        # Place under Blockout without separator
        register_tool(tools.mirror.ROTOR_MT_Mirror, group=False, separator=False, after={'bout.block_obj'})
    else:
        # Default: use separator
        register_tool(tools.mirror.ROTOR_MT_Mirror, group=False, separator=True)

    btypes.register()
    keymap.register()


def unregister():
    keymap.unregister()

    unregister_tool(tools.mirror.ROTOR_MT_Mirror)

    for cls in reversed(classes):
        unregister_class(cls)

    btypes.unregister()
    unload_icons()
