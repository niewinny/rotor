import bpy
from bpy.props import CollectionProperty, IntProperty
from ..utils import addon
from .mirror_utils import get_mirror_object, create_mirror_modifier, bisect_object
from .mirror_props import ROTOR_PG_MirrorObjectItem


class ROTOR_OT_AddMirrorAxis(bpy.types.Operator):
    """Add new mirror"""
    bl_idname = "rotor.add_mirror_axis"
    bl_label = "Rotor Mirror Axis"
    bl_options = {'REGISTER', 'UNDO'}

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis to toggle",
        items=[('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')],
    )
    sign: bpy.props.EnumProperty(
        name="Sign",
        description="Sign (+ or -)",
        items=[('POS', '+', ''), ('NEG', '-', '')],
    )
    
    affected_objects: CollectionProperty(type=ROTOR_PG_MirrorObjectItem)
    active_object_index: IntProperty(name="Active Object", default=0)

    def invoke(self, context, event):
        """Populate the list when operator is invoked"""
        # Clear and populate the list with current selection
        self.affected_objects.clear()
        active_object = context.active_object
        
        # Add active object first if it's a mesh
        if active_object and active_object.type == 'MESH' and active_object.select_get():
            item = self.affected_objects.add()
            item.name = active_object.name
            item.enabled = True
            # For Add operation, we will add modifiers so mark as having them
            item.has_mirror_modifier = True
        
        # Add other selected objects
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj != active_object:
                item = self.affected_objects.add()
                item.name = obj.name
                item.enabled = True
                # For Add operation, we will add modifiers so mark as having them
                item.has_mirror_modifier = True
        
        # Continue with normal execution
        return self.execute(context)

    def draw(self, context):
        """Draw checkboxes in the undo panel"""
        layout = self.layout
        
        if hasattr(self, 'affected_objects') and self.affected_objects:
            # Show object count
            layout.label(text=f"Affected Objects: {len(self.affected_objects)}")
            
            # Use template_list for scrollable list
            layout.template_list(
                "ROTOR_UL_MirrorObjectList", "",
                self, "affected_objects",
                self, "active_object_index",
                rows=min(len(self.affected_objects), 10),  # Show up to 10 rows
                maxrows=10
            )

    def execute(self, context):
        axis_map = {'X': 0, 'Y': 1, 'Z': 2}
        axis_idx = axis_map[self.axis]
        is_neg = self.sign == 'NEG'

        active_object = context.active_object
        pref = addon.pref().tools.mirror
        pivot = pref.pivot
        orientation = pref.orientation

        mirror_object, individual = get_mirror_object(context, active_object, pivot, orientation)

        # Get list of enabled objects
        enabled_objects = []
        if hasattr(self, 'affected_objects') and self.affected_objects:
            for item in self.affected_objects:
                if item.enabled and item.name in bpy.data.objects:
                    obj = bpy.data.objects[item.name]
                    if obj.type == 'MESH':
                        enabled_objects.append(obj)
        else:
            # First run - use all selected mesh objects
            enabled_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        affected_count = 0
        for obj in enabled_objects:
            if pref.bisect:
                bisect_object(obj, axis_idx, pivot, orientation, context, is_neg)

            create_mirror_modifier(context, obj, mirror_object, individual, axis_idx, is_neg)
            affected_count += 1

        # Report success
        self.report({'INFO'}, f"Added mirror modifiers to {affected_count} objects.")
        
        # Check if we should return to previous tool
        pref = addon.pref().tools.mirror
        last_tool = context.scene.rotor.ops.last_tool
        if pref.tool_fallback and last_tool:
            # Check if we're currently using the mirror tool
            current_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
            if current_tool and current_tool.idname == 'rotor.mirror_tool':
                try:
                    bpy.ops.wm.tool_set_by_id(name=last_tool)
                    # Clear the last tool to prevent stale references
                    context.scene.rotor.ops.last_tool = ""
                except:
                    # If switching fails, just continue
                    pass
        
        return {'FINISHED'}


classes = (
    ROTOR_OT_AddMirrorAxis,
)