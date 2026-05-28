from pathlib import Path

import bpy

from ...utils import addon


class ROTOR_MT_Mirror(bpy.types.WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "OBJECT"
    bl_idname = "mirror.mirror_tool"
    bl_label = "Mirror"
    bl_description = (
        f"v: {addon.version}\n\nTool for mirroring geometry"
        "\n • ALT + X - Call mirror gizmo"
        "\n • SPACE - Pick custom plane"
        "\n • Q - Cycle orientation"
        "\n • E - Cycle pivot"
    )
    bl_widget = "ROTOR_GGT_MirrorGizmoGroup"
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "mirror").as_posix()
    bl_keymap = (
        ("mirror.fallback_tool", {"type": "ESC", "value": "PRESS"}, None),
        (
            "mirror.pick_custom_plane",
            {"type": "SPACE", "value": "PRESS"},
            {"properties": [("target", "BOTH")]},
        ),
        ("mirror.set_orientation", {"type": "Q", "value": "PRESS"}, {"properties": [("cycle", True)]}),
        ("mirror.set_pivot", {"type": "E", "value": "PRESS"}, {"properties": [("cycle", True)]}),
    )

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

        row.prop(rotor, "real", text="Real")
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
            case "CUSTOM":
                label, icon = ("Custom", "OBJECT_ORIGIN")
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
            case "CUSTOM":
                label, icon = ("Custom", "OBJECT_ORIGIN")
        row.popover("ROTOR_PT_Pivot", text="", icon=icon)
        row.separator()
        sub = row.row(align=True)
        sub.popover("ROTOR_PT_ToolOptions", text="", icon="EMPTY_AXIS")
        mirror_opts = sub.row(align=True)
        mirror_opts.enabled = not rotor.real
        mirror_opts.popover("ROTOR_PT_MirrorOptions", text="", icon="MOD_MIRROR")


class ROTOR_MT_MirrorMesh(bpy.types.WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "EDIT_MESH"
    bl_idname = "mirror.mirror_mesh_tool"
    bl_label = "Mirror"
    bl_description = (
        f"v: {addon.version}\n\nTool for mirroring (symmetrizing) mesh geometry"
        "\n • Dots mirror the full mesh\n • Handles mirror the selection"
        "\n • SPACE - Pick custom plane"
        "\n • Q - Cycle orientation"
        "\n • E - Cycle pivot"
    )
    bl_widget = "ROTOR_GGT_MirrorMeshGizmoGroup"
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "mirror").as_posix()
    bl_keymap = (
        ("mirror.fallback_tool", {"type": "ESC", "value": "PRESS"}, None),
        (
            "mirror.pick_custom_plane",
            {"type": "SPACE", "value": "PRESS"},
            {"properties": [("target", "BOTH")]},
        ),
        ("mirror.set_orientation", {"type": "Q", "value": "PRESS"}, {"properties": [("cycle", True)]}),
        ("mirror.set_pivot", {"type": "E", "value": "PRESS"}, {"properties": [("cycle", True)]}),
    )

    def draw_settings(context, layout, tool):
        mesh = addon.pref().tools.mesh
        row = layout.row(align=True)

        row.label(text="Mirror:")
        row.prop(mesh, "merge", text="Merge")
        row.separator()
        row.prop(mesh, "tool_fallback", text="Tool Fallback")

        row.separator_spacer()

        label, icon = "Global", "ORIENTATION_GLOBAL"
        match mesh.orientation:
            case "GLOBAL":
                label, icon = ("Global", "ORIENTATION_GLOBAL")
            case "LOCAL":
                label, icon = ("Local", "ORIENTATION_LOCAL")
            case "CURSOR":
                label, icon = ("Cursor", "ORIENTATION_CURSOR")
            case "NORMAL":
                label, icon = ("Normal", "ORIENTATION_NORMAL")
            case "CUSTOM":
                label, icon = ("Custom", "OBJECT_ORIGIN")
        row.popover("ROTOR_PT_MeshOrientation", text=label, icon=icon)

        icon = "PIVOT_MEDIAN"
        match mesh.pivot:
            case "ACTIVE":
                icon = "PIVOT_ACTIVE"
            case "MEDIAN":
                icon = "PIVOT_MEDIAN"
            case "ORIGIN":
                icon = "OBJECT_ORIGIN"
            case "CURSOR":
                icon = "PIVOT_CURSOR"
            case "CUSTOM":
                icon = "OBJECT_ORIGIN"
        row.popover("ROTOR_PT_MeshPivot", text="", icon=icon)
        row.separator()
        sub = row.row(align=True)
        sub.popover("ROTOR_PT_MeshOptions", text="", icon="EMPTY_AXIS")
