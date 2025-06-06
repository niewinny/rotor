import bpy
import os
from mathutils import Vector
import gpu
from gpu_extras.batch import batch_for_shader
from ..utils import view3d


def get_rotor_array_node_group():
    """Get or load the rotor array node group from the blend file"""
    possible_names = ["Rotor Array", "RotorArray", "Array", "rotor_array", "rotor array"]

    # Check if any of these node groups already exist
    for name in possible_names:
        if name in bpy.data.node_groups:
            return bpy.data.node_groups[name]

    # Load the node group from the blend file
    addon_dir = os.path.dirname(os.path.dirname(__file__))
    blend_file_path = os.path.normpath(os.path.join(addon_dir, "nodes", "array.blend"))

    if not os.path.exists(blend_file_path):
        return None

    try:
        with bpy.data.libraries.load(blend_file_path, link=False) as (data_from, data_to):
            available_groups = list(data_from.node_groups)

            if not available_groups:
                return None

            # Try to find a matching node group name
            target_group = None
            for name in possible_names:
                if name in available_groups:
                    target_group = name
                    break

            # If no exact match, use the first available group
            if not target_group:
                target_group = available_groups[0]

            data_to.node_groups = [target_group]

        # Find the loaded node group
        for name in possible_names + [target_group]:
            if name in bpy.data.node_groups:
                return bpy.data.node_groups[name]

        # If still not found, check if any new groups were added
        current_groups = list(bpy.data.node_groups.keys())
        if current_groups:
            return bpy.data.node_groups[current_groups[0]]

        return None

    except Exception:
        return None


def get_array_modifier(obj, modifier_name=None):
    """Get the geometry nodes modifier with rotor array node group"""
    # Possible names for the array node group
    possible_names = ["Rotor Array", "RotorArray", "Array", "rotor_array", "rotor array"]

    for modifier in obj.modifiers:
        if modifier.type == 'NODES' and modifier.node_group:
            if modifier.node_group.name in possible_names:
                if modifier_name is None or modifier.name == modifier_name:
                    return modifier
    return None


def get_all_array_modifiers(obj):
    """Get all geometry nodes modifiers with rotor array node group"""
    # Possible names for the array node group
    possible_names = ["Rotor Array", "RotorArray", "Array", "rotor_array", "rotor array"]

    modifiers = []
    for modifier in obj.modifiers:
        if modifier.type == 'NODES' and modifier.node_group:
            if modifier.node_group.name in possible_names:
                modifiers.append(modifier)
    return modifiers


def has_array_modifier(obj):
    """Check if object has any rotor array geometry nodes modifier"""
    return len(get_all_array_modifiers(obj)) > 0


def get_array_values(obj, modifier_name=None):
    """Get X, Y, Z values from the array modifier"""
    modifier = get_array_modifier(obj, modifier_name)
    if not modifier:
        return Vector((0.0, 0.0, 0.0))

    # Get values directly using the known socket names
    x_val = modifier.get("Socket_2", 0.0)  # X
    y_val = modifier.get("Socket_7", 0.0)  # Y
    z_val = modifier.get("Socket_8", 0.0)  # Z

    return Vector((x_val, y_val, z_val))


def get_array_count(obj, modifier_name=None):
    """Get Count value from the array modifier"""
    modifier = get_array_modifier(obj, modifier_name)
    if not modifier:
        return 2

    # Get count value from Socket_3
    return int(modifier.get("Socket_3", 2))


def set_array_count(obj, count, modifier_name=None):
    """Set Count value in the array modifier"""
    modifier = get_array_modifier(obj, modifier_name)
    if not modifier:
        return False

    # Ensure minimum count of 2
    count = max(2, int(count))
    modifier["Socket_3"] = count

    # Force update of the object and its data
    obj.update_tag(refresh={'OBJECT', 'DATA'})

    # Update the dependency graph
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()

    # Update the view layer
    bpy.context.view_layer.update()

    return True


def set_array_value(obj, axis, value, modifier_name=None):
    """Set X, Y, or Z value in the array modifier"""
    modifier = get_array_modifier(obj, modifier_name)
    if not modifier:
        return False

    # Map axis to correct socket names
    socket_map = {
        'x': "Socket_2",  # X
        'y': "Socket_7",  # Y
        'z': "Socket_8"   # Z
    }

    socket_name = socket_map.get(axis.lower())
    if socket_name:
        modifier[socket_name] = value

        # Force update of the object and its data
        obj.update_tag(refresh={'OBJECT', 'DATA'})

        # Update the dependency graph
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()

        # Update the view layer
        bpy.context.view_layer.update()

        return True

    return False


class ROTOR_OT_AddArrayModifier(bpy.types.Operator):
    """Add geometry nodes array modifier to selected objects"""
    bl_idname = "rotor.add_array_modifier"
    bl_label = "Add Rotor Array Modifier"
    bl_options = {'REGISTER', 'UNDO'}

    axis: bpy.props.StringProperty(
        name="Axis",
        description="Initial axis to set (x, y, z)",
        default=""
    )

    def execute(self, context):
        node_group = get_rotor_array_node_group()
        if not node_group:
            self.report({'ERROR'}, "Could not load Rotor Array node group")
            return {'CANCELLED'}

        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_objects:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}

        for obj in selected_objects:
            # Check if object already has the modifier
            if has_array_modifier(obj):
                continue

            # Add geometry nodes modifier
            modifier = obj.modifiers.new(name="Rotor Array", type='NODES')
            modifier.node_group = node_group

            # Set default values using the correct socket names
            modifier["Socket_2"] = 2.0 if self.axis == 'x' else 0.0  # X
            modifier["Socket_3"] = 2  # Count
            modifier["Socket_7"] = 2.0 if self.axis == 'y' else 0.0  # Y
            modifier["Socket_8"] = 2.0 if self.axis == 'z' else 0.0  # Z

        return {'FINISHED'}


class ROTOR_OT_MoveArrayLocation(bpy.types.Operator):
    """Move array location with gizmo - modal operator for dragging"""
    bl_idname = "rotor.move_array_location"
    bl_label = "Rotor Array Move"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    offset: bpy.props.FloatVectorProperty(
        name="Offset",
        description="Movement offset",
        size=3,
        default=(0.0, 0.0, 0.0)
    )

    axis: bpy.props.StringProperty(
        name="Axis",
        description="Axis to move along (x, y, z)",
        default=""
    )

    modifier_name: bpy.props.StringProperty(
        name="Modifier Name",
        description="Name of the specific modifier to control",
        default=""
    )

    def invoke(self, context, event):
        """Start modal interaction"""
        self.active_object = context.active_object
        if not self.active_object:
            return {'CANCELLED'}

        # Check if target modifier exists
        if self.modifier_name:
            modifier = get_array_modifier(self.active_object, self.modifier_name)
            if not modifier:
                return {'CANCELLED'}
        else:
            # If no specific modifier, check if any exist or add one
            if not has_array_modifier(self.active_object):
                if self.axis:
                    bpy.ops.rotor.add_array_modifier(axis=self.axis)
                return {'FINISHED'}

        # Get initial values from the specific modifier
        array_values = get_array_values(self.active_object, self.modifier_name if self.modifier_name else None)
        if self.axis:
            axis_index = {'x': 0, 'y': 1, 'z': 2}[self.axis]
            self.initial_value = array_values[axis_index]
        else:
            self.initial_values = array_values.copy()

        self.initial_mouse = Vector((event.mouse_region_x, event.mouse_region_y))

        # Store initial click position for smooth dragging
        self.initial_axis_offset = Vector((0, 0, 0))

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}



    def modal(self, context, event):
        """Handle mouse movement during drag"""
        if event.type == 'MOUSEMOVE':
            active_obj = self.active_object
            if not active_obj or not has_array_modifier(active_obj):
                return {'CANCELLED'}

            # Get region and region_3d for coordinate conversion
            region = context.region
            region_3d = context.space_data.region_3d

            # Calculate mouse movement in viewport coordinates
            mouse_delta = Vector((event.mouse_region_x, event.mouse_region_y)) - self.initial_mouse

            # Get view vectors for screen-to-world conversion
            view_matrix_inv = region_3d.view_matrix.inverted()

            # Adaptive movement scale based on distance from camera
            array_values = get_array_values(active_obj)
            array_world_location = active_obj.location + Vector((array_values.x, array_values.y, array_values.z))
            camera_distance = (view_matrix_inv.translation - array_world_location).length
            movement_scale = max(camera_distance * 0.0005, 0.001)  # Scale with distance

            if self.axis:
                # Individual axis movement in local space
                axis_index = {'x': 0, 'y': 1, 'z': 2}[self.axis]

                # Get axis vector in object's local space
                axis_vector = Vector((0, 0, 0))
                axis_vector[axis_index] = 1.0

                # Transform axis to world space for screen projection
                world_axis_vector = active_obj.matrix_world.to_3x3() @ axis_vector

                # Get object center in screen space
                obj_center_2d = view3d.location_3d_to_region_2d(region, region_3d, active_obj.location)
                axis_end_3d = active_obj.location + world_axis_vector
                axis_end_2d = view3d.location_3d_to_region_2d(region, region_3d, axis_end_3d)

                if obj_center_2d and axis_end_2d:
                    # Calculate screen-space axis direction
                    screen_axis = (axis_end_2d - obj_center_2d).normalized()

                    # Calculate mouse movement along this screen axis
                    mouse_movement = mouse_delta.dot(screen_axis)

                    # Convert screen movement to local space movement
                    # Scale by distance for intuitive feel
                    local_movement = mouse_movement * movement_scale

                    # Update the modifier value in local space
                    new_value = self.initial_value + local_movement
                    set_array_value(active_obj, self.axis, new_value, self.modifier_name if self.modifier_name else None)
                else:
                    # Fallback: use simple X mouse movement
                    movement_amount = mouse_delta.x * movement_scale
                    new_value = self.initial_value + movement_amount
                    set_array_value(active_obj, self.axis, new_value, self.modifier_name if self.modifier_name else None)

            # Redraw viewport
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        elif event.type in {'LEFTMOUSE', 'RET'}:
            # Confirm movement
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Cancel movement - restore original values
            active_obj = self.active_object
            modifier_name = self.modifier_name if self.modifier_name else None
            if active_obj and (get_array_modifier(active_obj, modifier_name) is not None):
                if self.axis:
                    set_array_value(active_obj, self.axis, self.initial_value, modifier_name)
                else:
                    set_array_value(active_obj, 'x', self.initial_values.x, modifier_name)
                    set_array_value(active_obj, 'y', self.initial_values.y, modifier_name)
                    set_array_value(active_obj, 'z', self.initial_values.z, modifier_name)
            context.area.tag_redraw()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, _context):
        """Fallback for non-interactive calls"""
        active_obj = self.active_object
        if not active_obj or not has_array_modifier(active_obj):
            return {'CANCELLED'}

        if self.axis:
            # Individual axis movement
            axis_index = {'x': 0, 'y': 1, 'z': 2}[self.axis]
            modifier_name = self.modifier_name if self.modifier_name else None
            current_values = get_array_values(active_obj, modifier_name)
            new_value = current_values[axis_index] + self.offset[axis_index]
            set_array_value(active_obj, self.axis, new_value, modifier_name)

        return {'FINISHED'}


class ROTOR_OT_ScaleArrayCount(bpy.types.Operator):
    """Scale array count with gizmo - modal operator for scaling"""
    bl_idname = "rotor.scale_array_count"
    bl_label = "Rotor Array Scale Count"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    scale_factor: bpy.props.FloatProperty(
        name="Scale Factor",
        description="Scale factor for count",
        default=1.0
    )

    modifier_name: bpy.props.StringProperty(
        name="Modifier Name",
        description="Name of the specific modifier to control",
        default=""
    )
    
    def draw_line(self, context):
        """Draw line from gizmo center to mouse cursor"""
        if not hasattr(self, 'gizmo_center_2d') or not hasattr(self, 'current_mouse_2d'):
            return
            
        # Set proper GPU state
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(1.0)
        
        # Create shader and batch for line drawing
        shader = gpu.shader.from_builtin('POLYLINE_FLAT_COLOR')
        
        # Line coordinates in screen space with colors
        coords = [
            (self.gizmo_center_2d.x, self.gizmo_center_2d.y),
            (self.current_mouse_2d.x, self.current_mouse_2d.y)
        ]
        
        # Colors for each vertex (black)
        colors = [
            (0.0, 0.0, 0.0, 0.8),
            (0.0, 0.0, 0.0, 0.8)
        ]
        
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords, "color": colors})
        
        # Bind shader
        shader.bind()
        shader.uniform_float("lineWidth", 1.0)
        shader.uniform_float("viewportSize", (context.region.width, context.region.height))
        
        # Draw the line
        batch.draw(shader)
        
        # Reset GPU state
        gpu.state.blend_set('NONE')

    def invoke(self, context, event):
        """Start modal interaction"""
        self.active_object = context.active_object
        if not self.active_object:
            return {'CANCELLED'}

        # Check if target modifier exists
        if self.modifier_name:
            modifier = get_array_modifier(self.active_object, self.modifier_name)
            if not modifier:
                return {'CANCELLED'}
        else:
            # If no specific modifier, check if any exist
            if not has_array_modifier(self.active_object):
                return {'CANCELLED'}

        # Get initial count
        self.initial_count = get_array_count(self.active_object, self.modifier_name if self.modifier_name else None)

        # Calculate gizmo center in 2D screen space
        obj = self.active_object
        obj_matrix = obj.matrix_world

        # Get array values to find gizmo position
        array_values = get_array_values(obj, self.modifier_name if self.modifier_name else None)
        local_offset = Vector((array_values.x, array_values.y, array_values.z))
        world_offset = obj_matrix.to_3x3() @ local_offset
        array_location = Vector(obj.location) + world_offset

        # Gizmo is positioned in the middle between origin and array location
        gizmo_center_3d = (Vector(obj.location) + array_location) * 0.5

        # Convert gizmo center to 2D screen coordinates
        region = context.region
        region_3d = context.space_data.region_3d
        self.gizmo_center_2d = view3d.location_3d_to_region_2d(region, region_3d, gizmo_center_3d)

        if not self.gizmo_center_2d:
            return {'CANCELLED'}

        # Calculate initial distance from gizmo center to mouse
        initial_mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.initial_distance = (initial_mouse - self.gizmo_center_2d).length

        # Ensure minimum distance to avoid division by zero
        self.initial_distance = max(self.initial_distance, 10.0)

        # Add draw handler for line visualization
        self._draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_line, (context,), 'WINDOW', 'POST_PIXEL'
        )

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        """Handle mouse movement during scaling"""
        if event.type == 'MOUSEMOVE':
            active_obj = self.active_object
            modifier_name = self.modifier_name if self.modifier_name else None

            if not active_obj or not get_array_modifier(active_obj, modifier_name):
                return {'CANCELLED'}

            # Calculate current distance from gizmo center
            current_mouse = Vector((event.mouse_region_x, event.mouse_region_y))
            self.current_mouse_2d = current_mouse  # Store for drawing
            current_distance = (current_mouse - self.gizmo_center_2d).length

            distance_ratio = current_distance / self.initial_distance

            scaled_count = self.initial_count * distance_ratio

            new_count = max(2, int(round(scaled_count)))

            new_count = min(new_count, 50)

            set_array_count(active_obj, new_count, modifier_name)

            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        elif event.type in {'LEFTMOUSE', 'RET'}:
            # Remove draw handler
            if hasattr(self, '_draw_handler'):
                bpy.types.SpaceView3D.draw_handler_remove(self._draw_handler, 'WINDOW')
            # Confirm scaling
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Remove draw handler
            if hasattr(self, '_draw_handler'):
                bpy.types.SpaceView3D.draw_handler_remove(self._draw_handler, 'WINDOW')
            # Cancel scaling - restore original count
            active_obj = self.active_object
            modifier_name = self.modifier_name if self.modifier_name else None
            if active_obj and get_array_modifier(active_obj, modifier_name):
                set_array_count(active_obj, self.initial_count, modifier_name)
            context.area.tag_redraw()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, _context):
        """Fallback for non-interactive calls"""
        active_obj = self.active_object
        modifier_name = self.modifier_name if self.modifier_name else None
        if not active_obj or not get_array_modifier(active_obj, modifier_name):
            return {'CANCELLED'}

        current_count = get_array_count(active_obj, modifier_name)
        new_count = max(2, int(current_count * self.scale_factor))
        set_array_count(active_obj, new_count, modifier_name)

        return {'FINISHED'}


classes = (
    ROTOR_OT_AddArrayModifier,
    ROTOR_OT_MoveArrayLocation,
    ROTOR_OT_ScaleArrayCount,
)
