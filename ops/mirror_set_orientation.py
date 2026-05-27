"""Quick-set / cycle the Mirror tool orientation and pivot.

Used by the tool header buttons and the tool-scoped keymap:
orientation = G/L/N/C + Tab, pivot = Ctrl + initial + Ctrl+Tab. Writes to the
active tool's preference group (``tools.mirror`` in Object mode, ``tools.mesh``
in Edit mode). Requesting a value not available in the current mode
(e.g. Normal/Origin in Object mode) is a no-op.
"""

import bpy

from ..utils import addon


class ROTOR_OT_SetOrientation(bpy.types.Operator):
    """Set or cycle the Mirror tool orientation"""

    bl_idname = "mirror.set_orientation"
    bl_label = "Set Mirror Orientation"
    bl_options = {"INTERNAL"}

    orientation: bpy.props.EnumProperty(
        name="Orientation",
        items=[
            ("GLOBAL", "Global", "Global orientation"),
            ("LOCAL", "Local", "Local orientation"),
            ("NORMAL", "Normal", "Normal orientation (Edit mesh only)"),
            ("CURSOR", "Cursor", "3D Cursor orientation"),
            ("CUSTOM", "Custom", "Custom orientation"),
        ],
        default="GLOBAL",
    )
    cycle: bpy.props.BoolProperty(
        name="Cycle",
        description="Cycle to the next available orientation",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        return context.mode in {"OBJECT", "EDIT_MESH"}

    def execute(self, context):
        from ..tools.mirror.props import mesh_orientations, orientations

        tools = addon.pref().tools
        if context.mode == "EDIT_MESH":
            group = tools.mesh
            available = [item[0] for item in mesh_orientations]
        else:
            group = tools.mirror
            available = [item[0] for item in orientations]

        if self.cycle:
            try:
                i = available.index(group.orientation)
            except ValueError:
                i = -1
            group.orientation = available[(i + 1) % len(available)]
        elif self.orientation in available:
            group.orientation = self.orientation
        else:
            return {"CANCELLED"}

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        return {"FINISHED"}


class ROTOR_OT_SetPivot(bpy.types.Operator):
    """Set or cycle the Mirror tool pivot"""

    bl_idname = "mirror.set_pivot"
    bl_label = "Set Mirror Pivot"
    bl_options = {"INTERNAL"}

    pivot: bpy.props.EnumProperty(
        name="Pivot",
        items=[
            ("ACTIVE", "Active", "Active element"),
            ("INDIVIDUAL", "Individual", "Individual elements (Object mode)"),
            ("WORLD", "World", "World center (Object mode)"),
            ("MEDIAN", "Median", "Selection median (Edit mesh)"),
            ("ORIGIN", "Origin", "Object origin (Edit mesh)"),
            ("CURSOR", "Cursor", "3D Cursor"),
            ("CUSTOM", "Custom", "Custom point"),
        ],
        default="ACTIVE",
    )
    cycle: bpy.props.BoolProperty(
        name="Cycle",
        description="Cycle to the next available pivot",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        return context.mode in {"OBJECT", "EDIT_MESH"}

    def execute(self, context):
        from ..tools.mirror.props import mesh_pivots, pivots

        tools = addon.pref().tools
        if context.mode == "EDIT_MESH":
            group = tools.mesh
            available = [item[0] for item in mesh_pivots]
        else:
            group = tools.mirror
            available = [item[0] for item in pivots]

        if self.cycle:
            try:
                i = available.index(group.pivot)
            except ValueError:
                i = -1
            group.pivot = available[(i + 1) % len(available)]
        elif self.pivot in available:
            group.pivot = self.pivot
        else:
            return {"CANCELLED"}

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
        return {"FINISHED"}


classes = (ROTOR_OT_SetOrientation, ROTOR_OT_SetPivot)
