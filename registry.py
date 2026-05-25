import bpy
from bpy.utils import register_class, register_tool, unregister_class, unregister_tool

from . import btypes, gizmos, keymap, ops, preferences, tools
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
        if "blockout" in addon_name.lower() or "bout" in addon_name.lower():
            has_blockout = True

    # Register with appropriate settings
    if has_blockout:
        # Place under Blockout without separator
        register_tool(
            tools.mirror.ROTOR_MT_Mirror,
            group=True,
            separator=False,
            after={"object.bout_block_obj"},
        )
        register_tool(
            tools.align.ROTOR_MT_Align,
            group=False,
            separator=False,
            after={"mirror.mirror_tool"},
        )
    else:
        # Default: use separator
        register_tool(tools.mirror.ROTOR_MT_Mirror, group=True, separator=True)
        register_tool(
            tools.align.ROTOR_MT_Align,
            group=False,
            separator=False,
            after={"mirror.mirror_tool"},
        )

    btypes.register()
    keymap.register()


def unregister():
    keymap.unregister()

    unregister_tool(tools.align.ROTOR_MT_Align)
    unregister_tool(tools.mirror.ROTOR_MT_Mirror)

    for cls in reversed(classes):
        unregister_class(cls)

    btypes.unregister()
    unload_icons()
