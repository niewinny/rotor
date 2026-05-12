import bpy


class ROTOR_OT_SetActiveToolOperator(bpy.types.Operator):
    """Cycle between Mirror and Align; first press from another tool saves
    that tool so ESC can return to it."""

    bl_idname = "object.mirror_set_active_tool"
    bl_label = "Set Active Tool"

    def execute(self, context):
        active_tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        ).idname

        if active_tool == "mirror.mirror_tool":
            # Already on mirror — jump to align without touching last_tool
            # so ESC still returns to the user's original tool.
            bpy.ops.wm.tool_set_by_id(name="mirror.align_tool")
        elif active_tool == "mirror.align_tool":
            # Cycle back to mirror.
            bpy.ops.wm.tool_set_by_id(name="mirror.mirror_tool")
        else:
            # Coming from an external tool — remember it and enter mirror.
            context.scene.rotor.ops.last_tool = active_tool
            bpy.ops.wm.tool_set_by_id(name="mirror.mirror_tool")

        return {"FINISHED"}


classes = (ROTOR_OT_SetActiveToolOperator,)
