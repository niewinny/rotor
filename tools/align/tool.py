from pathlib import Path

import bpy

from ...utils import addon


class ROTOR_MT_Align(bpy.types.WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "OBJECT"
    bl_idname = "mirror.align_tool"
    bl_label = "Align"
    bl_description = f"v: {addon.version}\n\nTool for aligning selected objects to world origin or active object"
    bl_widget = "ROTOR_GGT_AlignGizmoGroup"
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "array").as_posix()
    bl_keymap = (("mirror.fallback_tool", {"type": "ESC", "value": "PRESS"}, None),)

    def draw_settings(context, layout, tool):
        rotor = addon.pref().tools.align
        row = layout.row(align=True)

        row.label(text="Align:")
        row.prop(rotor, "target_world", text="World", toggle=True, icon="WORLD")
        row.prop(rotor, "target_active", text="Active", toggle=True, icon="PIVOT_ACTIVE")
        row.prop(rotor, "target_cursor", text="Cursor", toggle=True, icon="CURSOR")
        row.separator()
        row.prop(rotor, "tool_fallback", text="Tool Fallback")

        row.separator_spacer()

        label, icon = ("Origin", "OBJECT_ORIGIN") if rotor.source == "ORIGIN" else ("Bounding Box", "PIVOT_BOUNDBOX")
        row.popover("ROTOR_PT_AlignSource", text=label, icon=icon)
        row.separator()
        sub = row.row(align=True)
        sub.enabled = rotor.target_active
        label, icon = ("Origin", "OBJECT_ORIGIN") if rotor.target_source == "ORIGIN" else ("Bounding Box", "PIVOT_BOUNDBOX")
        sub.popover("ROTOR_PT_AlignTargetSource", text=label, icon=icon)
        row.separator()
        label, icon = ("Global", "ORIENTATION_GLOBAL") if rotor.orientation == "GLOBAL" else ("Local", "ORIENTATION_LOCAL")
        row.popover("ROTOR_PT_AlignOrientation", text=label, icon=icon)
