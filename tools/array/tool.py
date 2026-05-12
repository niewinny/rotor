from pathlib import Path

import bpy

from ...utils import addon


class ROTOR_MT_Array(bpy.types.WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "OBJECT"
    bl_idname = "mirror.array_tool"
    bl_label = "Array"
    bl_description = f"v: {addon.version}\n\nTool for arraying objects"
    bl_widget = "ROTOR_GGT_ArrayGizmoGroup"
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "array").as_posix()
    bl_keymap = (("mirror.fallback_tool", {"type": "ESC", "value": "PRESS"}, None),)

    def draw_settings(context, layout, tool):
        dup = addon.pref().tools.array
        row = layout.row(align=True)

        row.prop(dup, "real", text="Real")
        row.separator()
        row.prop(dup, "mode", text="")
        row.prop(dup, "count")
        if dup.real:
            row.prop(dup, "scale")

        row.separator()

        row.label(text="Axis:")
        row.prop(dup, "axis_x", toggle=True)
        row.prop(dup, "axis_y", toggle=True)
        row.prop(dup, "axis_z", toggle=True)
        if dup.real:
            if dup.mode == "LINEAR":
                row.prop(dup, "double", toggle=True)
            row.prop(dup, "align", toggle=True)
        if dup.mode == "CIRCLE":
            row.prop(dup, "face_axis", text="Face")

        row.separator_spacer()

        row.prop(dup.snap, "orientation", text="")
        row.prop(dup.snap, "pivot", text="")
