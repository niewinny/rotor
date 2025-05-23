import bpy


class ROTOR_OT_SetActiveToolOperator(bpy.types.Operator):
    """Set Active Tool to Brush Select"""
    bl_idname = "rotor.set_active_tool"
    bl_label = "Set Active Tool"

    edit_mode: bpy.props.BoolProperty(name="Edit Mode", default=False)

    def execute(self, context):
        active_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False).idname

        tools = [
            'rotor.mirror_tool',
        ]

        if active_tool not in tools:
            bpy.ops.wm.tool_set_by_id(name="rotor.mirror_tool")


        return {'FINISHED'}


classes = (
    ROTOR_OT_SetActiveToolOperator,
)