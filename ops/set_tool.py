import bpy


class ROTOR_OT_SetActiveToolOperator(bpy.types.Operator):
    """Toggle the Mirror tool in Object Mode and the Mesh Mirror tool in Edit
    Mesh. The first press from another tool saves that tool so ESC can return
    to it."""

    bl_idname = "object.mirror_set_active_tool"
    bl_label = "Set Active Tool"

    def execute(self, context):
        tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        )
        active_tool = tool.idname if tool else ""

        if context.mode == "EDIT_MESH":
            if active_tool == "mirror.mirror_mesh_tool":
                # Already on the mesh mirror tool — toggle back to the
                # remembered tool, if any.
                last_tool = context.scene.rotor.ops.last_tool
                if last_tool:
                    try:
                        bpy.ops.wm.tool_set_by_id(name=last_tool)
                        context.scene.rotor.ops.last_tool = ""
                    except Exception:
                        pass
            else:
                # Coming from another tool — remember it and enter mirror.
                context.scene.rotor.ops.last_tool = active_tool
                bpy.ops.wm.tool_set_by_id(name="mirror.mirror_mesh_tool")
            return {"FINISHED"}

        if active_tool == "mirror.mirror_tool":
            # Already on the mirror tool — toggle back to the remembered tool,
            # if any.
            last_tool = context.scene.rotor.ops.last_tool
            if last_tool:
                try:
                    bpy.ops.wm.tool_set_by_id(name=last_tool)
                    context.scene.rotor.ops.last_tool = ""
                except Exception:
                    pass
        else:
            # Coming from another tool — remember it and enter mirror.
            context.scene.rotor.ops.last_tool = active_tool
            bpy.ops.wm.tool_set_by_id(name="mirror.mirror_tool")

        return {"FINISHED"}


classes = (ROTOR_OT_SetActiveToolOperator,)
