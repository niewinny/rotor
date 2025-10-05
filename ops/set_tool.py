import bpy
from ..utils import addon


class ROTOR_OT_SetActiveToolOperator(bpy.types.Operator):
    """Set Active Tool to Brush Select"""
    bl_idname = "object.rotor_set_active_tool"
    bl_label = "Set Active Tool"

    def execute(self, context):
        active_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False).idname

        tools = [
            'rotor.mirror_tool',
        ]

        if active_tool not in tools:
            # Store the current tool before switching
            context.scene.rotor.ops.last_tool = active_tool
            
            bpy.ops.wm.tool_set_by_id(name="rotor.mirror_tool")


        return {'FINISHED'}


classes = (
    ROTOR_OT_SetActiveToolOperator,
)