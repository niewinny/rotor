from pathlib import Path

import bpy

from ..utils import addon


class ROTOR_MT_Mirror(bpy.types.WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "OBJECT"
    bl_idname = "rotor.mirror_tool"
    bl_label = "Rotor: Mirror"
    bl_description = f"v: {addon.version}\n\nTool for mirroring geometry\n • ALT + X - Call mirror gizmo"
    bl_widget = "ROTOR_GGT_MirrorGizmoGroup"
    bl_icon = (Path(__file__).parent.parent / "icons" / "mirror").as_posix()
    bl_keymap = (("rotor.fallback_tool", {"type": "ESC", "value": "PRESS"}, None),)

    def draw_settings(context, layout, tool):
        rotor = addon.pref().tools.mirror
        row = layout.row(align=True)

        row.label(text="Mirror:")
        label = "None"
        _type = rotor.element
        match _type:
            case "OBJECT":
                label, icon = ("Objects", "OBJECT_DATAMODE")
            case "COLLECTION":
                label, icon = ("Collections", "OUTLINER_COLLECTION")
        row.popover("ROTOR_PT_Element", text=label, icon=icon)
        row.separator()

        row.prop(rotor, "bisect", text="Bisect")
        row.separator()
        row.prop(rotor, "tool_fallback", text="Tool Fallback")

        row.separator_spacer()

        label = "None"
        _type = rotor.orientation
        match _type:
            case "GLOBAL":
                label, icon = ("Global", "ORIENTATION_GLOBAL")
            case "LOCAL":
                label, icon = ("Local", "ORIENTATION_LOCAL")
            case "CURSOR":
                label, icon = ("Cursor", "ORIENTATION_CURSOR")
        row.popover("ROTOR_PT_Orientation", text=label, icon=icon)

        label = "None"
        _type = rotor.pivot
        match _type:
            case "ACTIVE":
                label, icon = ("Active Element", "PIVOT_ACTIVE")
            case "INDIVIDUAL":
                label, icon = ("Individual Elements", "PIVOT_INDIVIDUAL")
            case "WORLD":
                label, icon = ("World", "WORLD")
            case "CURSOR":
                label, icon = ("Cursor", "CURSOR")
        row.popover("ROTOR_PT_Pivot", text="", icon=icon)
        row.separator()
        sub = row.row(align=True)
        sub.popover("ROTOR_PT_ToolOptions", text="", icon="EMPTY_AXIS")
        sub.popover("ROTOR_PT_MirrorOptions", text="", icon="MOD_MIRROR")
