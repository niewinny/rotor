import bpy
from mathutils import Vector, Matrix
from ..utils import addon
from ..ops.array import has_array_modifier, get_array_values, get_all_array_modifiers, get_array_count

# Helper: axis info for arrows
alpha = 0.8
ARROW_AXES = [
    (Vector((1, 0, 0)), 'x', 'X'),   # Red +X
    (Vector((0, 1, 0)), 'y', 'Y'),   # Green +Y
    (Vector((0, 0, 1)), 'z', 'Z'),   # Blue +Z
]


def lighter(color, amt=0.5):
    """Make color lighter"""
    return tuple(
        min(1.0, v + (1.0 - v) * amt) if i < 3 else color[3]
        for i, v in enumerate(color)
    )


def create_arrow_gizmo(group, axis_letter, color, is_box=False, modifier_name=""):
    """Create interactive arrow gizmo for moving along specific axis"""
    gz = group.gizmos.new("GIZMO_GT_arrow_3d")
    gz.color = color[:3]
    gz.alpha = color[3]
    gz.color_highlight = lighter(color, 0.5)[:3]
    gz.alpha_highlight = color[3]
    gz.scale_basis = 1.0
    gz.use_draw_modal = False
    gz.hide_select = False  # Make it interactive
    gz.length = 2.0
    gz.matrix_basis = Matrix.Identity(4)
    
    # Set draw style based on whether modifier exists
    if is_box:
        gz.draw_style = 'BOX'
        gz.length = 1.5
        gz.scale_basis = 0.8
    
    # Use operator for arrow interaction
    props = gz.target_set_operator("rotor.move_array_location")
    props.axis = axis_letter.lower()  # Pass axis as 'x', 'y', or 'z'
    props.modifier_name = modifier_name  # Pass the specific modifier name

    return gz


def create_count_gizmo(group, color, modifier_name=""):
    """Create interactive circle gizmo for scaling count"""
    gz = group.gizmos.new("GIZMO_GT_move_3d")
    gz.color = color[:3]
    gz.alpha = 0.6  # Make it semi-transparent for better visibility
    gz.color_highlight = lighter(color, 0.3)[:3]
    gz.alpha_highlight = 0.8  # More visible when highlighted
    gz.scale_basis = 0.8  # Larger base scale for better interaction
    gz.use_draw_modal = False
    gz.hide_select = False  # Make it interactive
    gz.matrix_basis = Matrix.Identity(4)
    gz.draw_style = 'RING_2D'  # Circle style
    
    # Use operator for count scaling
    props = gz.target_set_operator("rotor.scale_array_count")
    props.modifier_name = modifier_name  # Pass the specific modifier name

    return gz


class ROTOR_GGT_ArrayGizmoGroup(bpy.types.GizmoGroup):
    """
    GizmoGroup for Rotor Array Tool. Displays X, Y, Z arrow gizmos for array manipulation.
    """
    bl_idname = "ROTOR_GGT_ArrayGizmoGroup"
    bl_label = "Rotor Array Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'SHOW_MODAL_ALL'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gizmos_arrows = []  # List of (gizmo, axis_letter, axis_vec, modifier_name) tuples
        self.gizmos_count = []   # List of (gizmo, modifier_name) tuples for count control

    @classmethod
    def poll(cls, _context) -> bool:
        """Show gizmos only when the rotor array tool is active and objects are selected."""
        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        return bool(active_tool and active_tool.idname == 'rotor.array_tool' and selected_objects)

    def setup(self, context):
        """Create arrow gizmos for X, Y, Z axes for each array modifier"""
        # Clear any existing gizmos
        self.gizmos_arrows.clear()
        self.gizmos_count.clear()
        
        # We'll create gizmos in draw_prepare since setup runs before we have object context

    def draw_prepare(self, context):
        """Update arrow gizmo positions and orientations"""
        if not context.active_object or context.active_object.type != 'MESH':
            return

        obj = context.active_object
        obj_location = Vector(obj.location)
        obj_matrix = obj.matrix_world
        
        # Get all array modifiers
        array_modifiers = get_all_array_modifiers(obj)
        
        # Determine how many gizmos we need
        # Arrow gizmos: 3 per modifier, plus 3 for "add modifier" if none exist
        needed_arrow_gizmos = len(array_modifiers) * 3 if array_modifiers else 3
        # Count gizmos: 1 per existing modifier
        needed_count_gizmos = len(array_modifiers)
        
        # Ensure we have the right number of gizmos
        self._ensure_gizmos(needed_arrow_gizmos, needed_count_gizmos, array_modifiers)
        
        # Update all gizmos
        if array_modifiers:
            # Update gizmos for each modifier
            self._update_modifier_gizmos(obj, obj_matrix, array_modifiers)
        else:
            # Show "add modifier" gizmos at object origin
            self._update_add_modifier_gizmos(obj_matrix, obj_location)

    def _ensure_gizmos(self, needed_arrow_count, needed_count_count, array_modifiers):
        """Ensure we have the right number of gizmos"""
        theme_axis = addon.pref().theme.axis
        
        # Manage arrow gizmos
        # Remove excess arrow gizmos
        while len(self.gizmos_arrows) > needed_arrow_count:
            gz, _, _, _ = self.gizmos_arrows.pop()
            self.gizmos.remove(gz)
        
        # Add missing arrow gizmos
        while len(self.gizmos_arrows) < needed_arrow_count:
            gizmo_index = len(self.gizmos_arrows)
            axis_index = gizmo_index % 3
            modifier_index = gizmo_index // 3
            
            axis_vec, axis_name, axis_letter = ARROW_AXES[axis_index]
            color = getattr(theme_axis, axis_name)
            
            # Determine modifier name
            if array_modifiers and modifier_index < len(array_modifiers):
                modifier_name = array_modifiers[modifier_index].name
                is_box = False
            else:
                modifier_name = ""
                is_box = True
            
            gz = create_arrow_gizmo(self, axis_letter, color, is_box, modifier_name)
            self.gizmos_arrows.append((gz, axis_letter, axis_vec, modifier_name))
        
        # Manage count gizmos
        # Remove excess count gizmos
        while len(self.gizmos_count) > needed_count_count:
            gz, _ = self.gizmos_count.pop()
            self.gizmos.remove(gz)
        
        # Add missing count gizmos
        while len(self.gizmos_count) < needed_count_count:
            modifier_index = len(self.gizmos_count)
            
            if modifier_index < len(array_modifiers):
                modifier_name = array_modifiers[modifier_index].name
                # Use neutral color for count gizmos
                color = theme_axis.n  # Yellow/neutral color
                
                gz = create_count_gizmo(self, color, modifier_name)
                self.gizmos_count.append((gz, modifier_name))
    
    def _update_modifier_gizmos(self, obj, obj_matrix, array_modifiers):
        """Update gizmos for existing modifiers"""
        axis_matrices = {
            'X': Matrix(([0, 0, 1], [0, 1, 0], [-1, 0, 0])),
            'Y': Matrix(([1, 0, 0], [0, 0, 1], [0, -1, 0])),
            'Z': Matrix(([1, 0, 0], [0, 1, 0], [0, 0, 1])),
        }
        
        for modifier_index, modifier in enumerate(array_modifiers):
            # Get array values for this modifier
            array_values = get_array_values(obj, modifier.name)
            
            # Transform local array offset to world space
            local_offset = Vector((array_values.x, array_values.y, array_values.z))
            world_offset = obj_matrix.to_3x3() @ local_offset
            arrow_location = Vector(obj.location) + world_offset
            
            # Update the 3 gizmos for this modifier (X, Y, Z)
            for axis_index in range(3):
                gizmo_index = modifier_index * 3 + axis_index
                if gizmo_index < len(self.gizmos_arrows):
                    gz, axis_letter, _, _ = self.gizmos_arrows[gizmo_index]
                    
                    # Regular arrow style
                    gz.draw_style = 'NORMAL'
                    gz.length = 2.0
                    gz.scale_basis = 1.0
                    
                    # Position arrow
                    arrow_matrix = axis_matrices[axis_letter].to_4x4()
                    rot_mat = obj_matrix.to_3x3().normalized().to_4x4()
                    arrow_matrix = rot_mat @ arrow_matrix
                    arrow_matrix.translation = arrow_location
                    gz.matrix_basis = arrow_matrix
        
        # Update count gizmos (positioned in the middle between origin and array location)
        for modifier_index, modifier in enumerate(array_modifiers):
            if modifier_index < len(self.gizmos_count):
                gz, _ = self.gizmos_count[modifier_index]
                
                # Get array values for this modifier to calculate middle position
                array_values = get_array_values(obj, modifier.name)
                local_offset = Vector((array_values.x, array_values.y, array_values.z))
                world_offset = obj_matrix.to_3x3() @ local_offset
                array_location = Vector(obj.location) + world_offset
                
                # Position in the middle between origin and array location
                middle_location = (Vector(obj.location) + array_location) * 0.5
                
                # Create matrix that faces the camera
                region_3d = bpy.context.space_data.region_3d
                if region_3d:
                    view_matrix = region_3d.view_matrix
                    # Create billboard matrix (always facing camera)
                    billboard_matrix = view_matrix.inverted().to_3x3().normalized().to_4x4()
                    billboard_matrix.translation = middle_location
                    
                    # Scale based on count for visual feedback
                    count = get_array_count(obj, modifier.name)
                    # Scale grows with count but stays reasonable
                    scale = 0.5 + (count - 2) * 0.05  # More subtle scaling
                    scale = min(scale, 1.5)  # Cap the maximum scale
                    scale_matrix = Matrix.Scale(scale, 4)
                    gz.matrix_basis = billboard_matrix @ scale_matrix
                else:
                    # Fallback if no region_3d
                    gz.matrix_basis = Matrix.Translation(middle_location)
    
    def _update_add_modifier_gizmos(self, obj_matrix, obj_location):
        """Update gizmos for adding new modifiers"""
        axis_matrices = {
            'X': Matrix(([0, 0, 1], [0, 1, 0], [-1, 0, 0])),
            'Y': Matrix(([1, 0, 0], [0, 0, 1], [0, -1, 0])),
            'Z': Matrix(([1, 0, 0], [0, 1, 0], [0, 0, 1])),
        }
        
        for gizmo_index in range(min(3, len(self.gizmos_arrows))):
            gz, axis_letter, _, _ = self.gizmos_arrows[gizmo_index]
            
            # Box arrow style to indicate "add modifier" action
            gz.draw_style = 'BOX'
            gz.length = 1.5
            gz.scale_basis = 0.8
            
            # Position arrow at object origin
            arrow_matrix = axis_matrices[axis_letter].to_4x4()
            rot_mat = obj_matrix.to_3x3().normalized().to_4x4()
            arrow_matrix = rot_mat @ arrow_matrix
            arrow_matrix.translation = obj_location
            gz.matrix_basis = arrow_matrix


classes = (
    ROTOR_GGT_ArrayGizmoGroup,
)
