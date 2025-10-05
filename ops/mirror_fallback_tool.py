import bpy


class ROTOR_OT_FallbackTool(bpy.types.Operator):
    """Return to previous tool"""
    bl_idname = "rotor.fallback_tool"
    bl_label = "Return to Previous Tool"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    @classmethod
    def poll(cls, context):
        # Only available when mirror tool is active
        current_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        return current_tool and current_tool.idname == 'rotor.mirror_tool'

    def execute(self, context):
        # Get the last tool from scene properties
        last_tool = context.scene.rotor.ops.last_tool
        
        if last_tool:
            # Check if we're currently using the mirror tool
            current_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
            if current_tool and current_tool.idname == 'rotor.mirror_tool':
                try:
                    bpy.ops.wm.tool_set_by_id(name=last_tool)
                    # Clear the last tool to prevent stale references
                    context.scene.rotor.ops.last_tool = ""
                    self.report({'INFO'}, f"Switched to {last_tool}")
                except:
                    self.report({'WARNING'}, "Failed to switch to previous tool")
            else:
                self.report({'INFO'}, "Not using mirror tool")
        else:
            self.report({'INFO'}, "No previous tool stored")
            
        return {'FINISHED'}


classes = (
    ROTOR_OT_FallbackTool,
)