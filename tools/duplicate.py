from pathlib import Path

import bpy

from ..utils import addon


class ROTOR_MT_Duplicate(bpy.types.WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "OBJECT"
    bl_idname = "rotor.duplicate_tool"
    bl_label = "Rotor: Duplicate"
    bl_description = f"v: {addon.version}\n\nTool for duplicating objects"
    bl_widget = "ROTOR_GGT_DuplicateGizmoGroup"
    bl_icon = (Path(__file__).parent.parent / "icons" / "duplicate").as_posix()
    bl_keymap = (("rotor.fallback_tool", {"type": "ESC", "value": "PRESS"}, None),)

    def draw_settings(context, layout, tool):
        pass
