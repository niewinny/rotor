import bpy
from pathlib import Path
from ..utils import addon


class ROTOR_MT_Array(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = 'rotor.array_tool'
    bl_label = 'Rotor: Array'
    bl_description = 'Tool for creating arrays of objects using geometry nodes'
    bl_widget = 'ROTOR_GGT_ArrayGizmoGroup'
    bl_icon = (Path(__file__).parent.parent / "icons" / "mirror").as_posix()  # Reusing mirror icon for now

    @staticmethod
    def draw_settings(context, layout, _tool):
        """Draw tool settings in the toolbar"""
        layout.label(text="Array Tool")
        layout.separator()
        
        # Show information about selected object
        if context.active_object and context.active_object.type == 'MESH':
            from ..ops.array import get_all_array_modifiers, get_array_values, get_array_count
            
            obj = context.active_object
            array_modifiers = get_all_array_modifiers(obj)
            
            if array_modifiers:
                layout.label(text=f"{len(array_modifiers)} Rotor Array modifier(s)")
                
                # Show each modifier's values
                for i, modifier in enumerate(array_modifiers):
                    col = layout.column(align=True)
                    col.label(text=f"{modifier.name}:")
                    
                    # Show count
                    count = get_array_count(obj, modifier.name)
                    col.label(text=f"Count: {count}")
                    
                    # Show offset values
                    array_values = get_array_values(obj, modifier.name)
                    row = col.row(align=True)
                    row.label(text=f"X: {array_values.x:.2f}")
                    row.label(text=f"Y: {array_values.y:.2f}")
                    row.label(text=f"Z: {array_values.z:.2f}")
                    
                    if i < len(array_modifiers) - 1:
                        layout.separator()
            else:
                layout.label(text="Click arrow gizmos to add array modifier")
        else:
            layout.label(text="Select a mesh object")


# We no longer need the Array PropertyGroup since we're using geometry nodes
# The modifier stores all the data we need

types_classes = (
    # Empty tuple - no property groups needed
)

classes = (
    # Empty tuple - no additional classes needed
)