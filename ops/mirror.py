import bpy
import bmesh
from bpy.props import BoolProperty, CollectionProperty, StringProperty, IntProperty
from bpy.types import PropertyGroup, UIList
from ..utils import addon
from mathutils import Matrix, Vector


# Mirror axis state transition table
# Key: (use_axis, use_bisect_flip, is_neg)
# Value: (new_use_axis, new_use_bisect_flip)
MIRROR_AXIS_TRANSITIONS = {
    (False, False, False): (True, False),   # Enable positive
    (False, False, True):  (True, True),    # Enable negative
    (True, False, False):  (False, False),  # Disable from positive
    (True, False, True):   (True, True),    # Switch to negative
    (True, True, False):   (True, False),   # Switch to positive
    (True, True, True):    (False, False),  # Disable from negative
}


class ROTOR_PG_MirrorObjectItem(PropertyGroup):
    """Property group for object items in mirror operations"""
    name: StringProperty(name="Object Name")
    enabled: BoolProperty(name="Enabled", default=True)
    has_mirror_modifier: BoolProperty(name="Has Mirror Modifier", default=False)


class ROTOR_PG_MirrorCollectionItem(PropertyGroup):
    """Property group for collection items in mirror operations"""
    name: StringProperty(name="Collection Name")
    enabled: BoolProperty(name="Enabled", default=True)


class ROTOR_UL_MirrorObjectList(UIList):
    """UIList for displaying mirror objects"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            
            # Get the operator's is_disabling state
            is_disabling = getattr(data, 'is_disabling', False)
            
            # Check if object has mirror modifier to enable/disable checkbox
            if not item.has_mirror_modifier and is_disabling:
                # Only disable if we're trying to disable and object has no modifier
                row.enabled = False
            
            row.prop(item, "enabled", text="")
            
            # Choose icon based on active object and mirror modifier status
            if not item.has_mirror_modifier and is_disabling:
                # Objects without mirror modifiers get an error icon only when disabling
                icon_type = 'ERROR'
            elif context.active_object and item.name == context.active_object.name:
                # Active object
                icon_type = 'OBJECT_HIDDEN'
            else:
                # Other objects
                icon_type = 'OBJECT_DATA'
            
            # Show object name
            row.label(text=item.name, icon=icon_type)
            
            # Add tag for new/edit status
            if item.has_mirror_modifier:
                row.label(text="[Edit]")
            elif not is_disabling:
                # Will create new modifier when enabling
                row.label(text="[New]")
            # No tag when disabling and no modifier exists
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='OBJECT_DATA')


class ROTOR_OT_SetMirrorAxis(bpy.types.Operator):
    """Set mirror axis"""
    bl_idname = "rotor.set_mirror_axis"
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
    is_disabling: BoolProperty(name="Is Disabling", default=False)

    def invoke(self, context, event):
        """Populate the list when operator is invoked"""
        # Clear and populate the list with current selection
        self.affected_objects.clear()
        active_object = context.active_object
        objects_without_modifiers = 0
        
        # Check if we're enabling or disabling based on active object
        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[self.axis]
        is_neg = self.sign == 'NEG'
        is_disabling = False
        
        if active_object and active_object.type == 'MESH':
            active_mirror_mod = next((m for m in reversed(active_object.modifiers) if m.type == 'MIRROR'), None)
            if active_mirror_mod:
                # Check if we're trying to disable the axis
                current_state = (active_mirror_mod.use_axis[axis_idx], 
                               active_mirror_mod.use_bisect_flip_axis[axis_idx], 
                               is_neg)
                new_axis, _ = MIRROR_AXIS_TRANSITIONS[current_state]
                is_disabling = (active_mirror_mod.use_axis[axis_idx] and not new_axis)
        
        # Add active object first if it's a mesh
        if active_object and active_object.type == 'MESH' and active_object.select_get():
            item = self.affected_objects.add()
            item.name = active_object.name
            item.enabled = True
            # Check if it has a mirror modifier
            has_mirror = any(m.type == 'MIRROR' for m in active_object.modifiers)
            item.has_mirror_modifier = has_mirror
            if not has_mirror:
                objects_without_modifiers += 1
        
        # Add other selected objects
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj != active_object:
                item = self.affected_objects.add()
                item.name = obj.name
                item.enabled = True
                # Check if it has a mirror modifier
                has_mirror = any(m.type == 'MIRROR' for m in obj.modifiers)
                item.has_mirror_modifier = has_mirror
                if not has_mirror:
                    objects_without_modifiers += 1
        
        # Store is_disabling state for use in draw methods
        self.is_disabling = is_disabling
        
        # Only show warning if we're disabling and objects don't have modifiers
        if is_disabling and objects_without_modifiers > 0:
            self.report({'WARNING'}, f"Cannot disable mirror on {objects_without_modifiers} objects without mirror modifiers.")
        
        # Continue with normal execution
        return self.execute(context)
    
    def draw(self, context):
        """Draw checkboxes in the undo panel"""
        layout = self.layout
        
        if hasattr(self, 'affected_objects') and self.affected_objects:
            # Use the stored is_disabling state
            is_disabling = self.is_disabling
            
            # Count objects with and without modifiers
            objects_with_modifiers = sum(1 for item in self.affected_objects if item.has_mirror_modifier)
            objects_without_modifiers = len(self.affected_objects) - objects_with_modifiers
            
            # Show object count
            if is_disabling and objects_without_modifiers > 0:
                layout.label(text=f"Affected Objects: {objects_with_modifiers} (Cannot disable on {objects_without_modifiers} without modifiers)", icon='ERROR')
            elif not is_disabling and objects_without_modifiers > 0:
                layout.label(text=f"Affected Objects: {len(self.affected_objects)} ({objects_without_modifiers} will get new modifiers)")
            else:
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
        
        # Track results
        affected_count = 0
        skipped_count = 0


        def toggle_axis(use_axis, use_bisect_flip, use_bisect, axis_idx, is_neg):
            # Apply transition based on current state
            key = (use_axis[axis_idx], use_bisect_flip[axis_idx], is_neg)
            new_axis, new_bisect_flip = MIRROR_AXIS_TRANSITIONS[key]
            use_axis[axis_idx] = new_axis
            use_bisect_flip[axis_idx] = new_bisect_flip
            use_bisect[axis_idx] = True

        # First check active object to determine if we're enabling or disabling
        active_mirror_mod = next((m for m in reversed(active_object.modifiers) if m.type == 'MIRROR'), None)
        is_disabling = False
        
        if active_mirror_mod:
            # Check if we're trying to disable the axis
            current_state = (active_mirror_mod.use_axis[axis_idx], 
                           active_mirror_mod.use_bisect_flip_axis[axis_idx], 
                           is_neg)
            new_axis, _ = MIRROR_AXIS_TRANSITIONS[current_state]
            is_disabling = (active_mirror_mod.use_axis[axis_idx] and not new_axis)
        
        # Always calculate mirror object based on current settings
        # This ensures newly created modifiers use the correct pivot/orientation
        mirror_object, individual = _get_mirror_object(context, active_object, pivot, orientation)

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
        
        for obj in enabled_objects:
            # Find existing mirror modifier
            mirror_mod = next((m for m in reversed(obj.modifiers) if m.type == 'MIRROR'), None)
            
            if mirror_mod is None:
                if is_disabling:
                    # Can't disable on objects without modifiers
                    skipped_count += 1
                    continue
                else:
                    # Enabling - create the modifier
                    if pref.bisect:
                        _bisect_object(obj, axis_idx, pivot, orientation, context)
                    
                    _create_mirror_modifier(context, obj, mirror_object, individual, axis_idx, is_neg)
                    affected_count += 1
                    continue

            # Set up axis and bisect options
            use_axis = mirror_mod.use_axis
            use_bisect_flip = mirror_mod.use_bisect_flip_axis
            use_bisect = mirror_mod.use_bisect_axis

            toggle_axis(use_axis, use_bisect_flip, use_bisect, axis_idx, is_neg)
            affected_count += 1

        # Report results
        if is_disabling:
            if skipped_count > 0 and affected_count > 0:
                self.report({'WARNING'}, f"Disabled mirror on {affected_count} objects. Could not disable on {skipped_count} objects without mirror modifiers.")
            elif skipped_count > 0 and affected_count == 0:
                self.report({'ERROR'}, f"Could not disable mirror. {skipped_count} objects have no mirror modifiers.")
                return {'CANCELLED'}
            else:
                self.report({'INFO'}, f"Disabled mirror on {affected_count} objects.")
        else:
            # Enabling - we create modifiers if needed
            self.report({'INFO'}, f"Modified {affected_count} objects.")

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

        mirror_object, individual = _get_mirror_object(context, active_object, pivot, orientation)

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
                _bisect_object(obj, axis_idx, pivot, orientation, context)

            _create_mirror_modifier(context, obj, mirror_object, individual, axis_idx, is_neg)
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


class ROTOR_OT_FallbackTool(bpy.types.Operator):
    """Return to previous tool"""
    bl_idname = "rotor.fallback_tool"
    bl_label = "Return to Previous Tool"
    bl_options = {'REGISTER'}
    
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


class ROTOR_OT_AddMirrorCollection(bpy.types.Operator):
    bl_idname = "rotor.add_mirror_collection"
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
    
    affected_collections: CollectionProperty(type=ROTOR_PG_MirrorCollectionItem)

    def invoke(self, context, event):
        """Populate the list when operator is invoked"""
        # Clear and populate the list with current selection
        self.affected_collections.clear()
        selected_objs = context.selected_objects
        collections = set()
        for obj in selected_objs:
            for col in getattr(obj, 'users_collection', []):
                # Ignore master collection and hidden/internal ones
                if not col.library and col.name != 'Scene Collection':
                    collections.add(col)
        
        for col in collections:
            item = self.affected_collections.add()
            item.name = col.name
            item.enabled = True
        
        # Continue with normal execution
        return self.execute(context)

    def draw(self, context):
        """Draw checkboxes in the undo panel"""
        layout = self.layout
        
        if hasattr(self, 'affected_collections') and self.affected_collections:
            layout.label(text=f"Affected Collections: {len(self.affected_collections)}")
            # For collections, we'll keep the simple list approach since there's no UIList for collections
            for item in self.affected_collections:
                row = layout.row()
                row.prop(item, "enabled", text=item.name)

    def execute(self, context):
        axis_map = {'X': 0, 'Y': 1, 'Z': 2}
        axis_idx = axis_map[self.axis]
        is_neg = self.sign == 'NEG'

        # Get mirror tool preferences
        pref = addon.pref().tools.mirror
        pivot = pref.pivot
        orientation = pref.orientation
        
        # Get enabled collections
        enabled_collections = []
        if hasattr(self, 'affected_collections') and self.affected_collections:
            for item in self.affected_collections:
                if item.enabled and item.name in bpy.data.collections:
                    col = bpy.data.collections[item.name]
                    enabled_collections.append(col)
        else:
            # First run - get all collections from selected objects
            selected_objs = context.selected_objects
            collections = set()
            for obj in selected_objs:
                for col in getattr(obj, 'users_collection', []):
                    # Ignore master collection and hidden/internal ones
                    if not col.library and col.name != 'Scene Collection':
                        collections.add(col)
            enabled_collections = list(collections)

        # Avoid double instancing
        created = set()
        for col in enabled_collections:
            if col in created:
                continue
            created.add(col)

            # Perform bisect operation if preference is enabled
            if pref.bisect:
                mesh_objects = [obj for obj in col.objects if obj.type == 'MESH']
                for obj in mesh_objects:
                    _bisect_object(obj, axis_idx, pivot, orientation, context)

            # Create an empty to instance the collection
            empty = bpy.data.objects.new(f"RotorMirrorInstance_{col.name}", None)
            empty.instance_type = 'COLLECTION'
            empty.instance_collection = col
            empty.empty_display_type = 'PLAIN_AXES'

            # Always use -1 scale for mirroring on the selected axis
            scale_vec = [1.0, 1.0, 1.0]
            scale_vec[axis_idx] = -1.0
            mirror_mat = Matrix.Scale(scale_vec[0], 4, Vector((1,0,0))) @ \
                         Matrix.Scale(scale_vec[1], 4, Vector((0,1,0))) @ \
                         Matrix.Scale(scale_vec[2], 4, Vector((0,0,1)))

            if pivot == 'WORLD':
                pivot_point = Vector((0,0,0))
            elif pivot == 'ACTIVE' and context.active_object:
                pivot_point = context.active_object.location.copy()
            elif pivot == 'INDIVIDUAL':
                objs_in_col = [o for o in col.objects if o.type == 'MESH']
                if objs_in_col:
                    locs = [o.location for o in objs_in_col]
                    pivot_point = sum(locs, Vector((0,0,0))) / len(locs)
                else:
                    pivot_point = Vector((0,0,0))
            elif pivot == 'CURSOR':
                pivot_point = context.scene.cursor.location.copy()
            else:
                pivot_point = Vector((0,0,0))

            # Compose the correct transformation: T @ R @ S @ R_inv @ T_inv
            rot_mat = None
            if orientation == 'LOCAL':
                if pivot == 'ACTIVE' and context.active_object:
                    rot_mat = context.active_object.rotation_euler.to_matrix().to_4x4()
                elif pivot == 'INDIVIDUAL':
                    objs_in_col = [o for o in col.objects if o.type == 'MESH']
                    if objs_in_col:
                        mats = [o.rotation_euler.to_matrix().to_4x4() for o in objs_in_col]
                        avg_mat = sum(mats, Matrix()) * (1.0 / len(mats))
                        rot_mat = avg_mat
                elif pivot in ('WORLD', 'CURSOR'):
                    # For LOCAL orientation with WORLD or CURSOR pivot, use collection objects' average rotation
                    objs_in_col = [o for o in col.objects if o.type == 'MESH']
                    if objs_in_col:
                        mats = [o.rotation_euler.to_matrix().to_4x4() for o in objs_in_col]
                        avg_mat = sum(mats, Matrix()) * (1.0 / len(mats))
                        rot_mat = avg_mat
            elif orientation == 'CURSOR':
                # CURSOR orientation uses cursor rotation regardless of pivot
                rot_mat = context.scene.cursor.rotation_euler.to_matrix().to_4x4()
            # For GLOBAL orientation, rot_mat stays None

            T = Matrix.Translation(pivot_point)
            T_inv = Matrix.Translation(-pivot_point)
            S = mirror_mat
            if rot_mat is not None:
                R = rot_mat
                R_inv = rot_mat.inverted()
                mirror_xform = T @ R @ S @ R_inv @ T_inv
            else:
                mirror_xform = T @ S @ T_inv

            empty.matrix_world = mirror_xform
            # Link empty to the Scene Collection, not to the instanced collection
            bpy.context.scene.collection.objects.link(empty)

        # Report success
        if len(created) > 0:
            self.report({'INFO'}, f"Mirrored {len(created)} collections.")
        else:
            self.report({'WARNING'}, "No collections were mirrored.")
        
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


def _get_mirror_object(context, obj, pivot, orientation):
    mirror_object = None
    individual = False

    match (pivot, orientation):
        case ('ACTIVE', 'LOCAL'):
            mirror_object = obj
        case ('ACTIVE', 'GLOBAL'):
            mirror_object = _create_empty_mirror_object(context, obj.location)
        case ('ACTIVE', 'CURSOR'):
            mirror_object = _create_empty_mirror_object(context, obj.location, orientation=context.scene.cursor.rotation_euler)
        case ('INDIVIDUAL', 'LOCAL'):
            mirror_object = None
        case ('INDIVIDUAL', 'GLOBAL'):
            individual = True
        case ('INDIVIDUAL', 'CURSOR'):
            individual = True
        case ('WORLD', 'LOCAL'):
            mirror_object = _create_empty_mirror_object(context, (0.0, 0.0, 0.0), orientation=obj.rotation_euler)
        case ('WORLD', 'GLOBAL'):
            mirror_object = _create_empty_mirror_object(context, (0.0, 0.0, 0.0))
        case ('WORLD', 'CURSOR'):
            mirror_object = _create_empty_mirror_object(context, (0.0, 0.0, 0.0), orientation=context.scene.cursor.rotation_euler)
        case ('CURSOR', 'LOCAL'):
            mirror_object = _create_empty_mirror_object(context, context.scene.cursor.location, orientation=obj.rotation_euler)
        case ('CURSOR', 'GLOBAL'):
            mirror_object = _create_empty_mirror_object(context, context.scene.cursor.location)
        case ('CURSOR', 'CURSOR'):
            mirror_object = _create_empty_mirror_object(context, context.scene.cursor.location, orientation=context.scene.cursor.rotation_euler)

    return mirror_object, individual



def _create_mirror_modifier(context, obj, mirror_object, individual, axis_idx, is_neg):
    """Create a mirror modifier for the given object"""

    _mirror_object = mirror_object

    if mirror_object == obj:
        _mirror_object = None

    if individual:
        _mirror_object = _create_empty_mirror_object(context, obj.location)

    mirror_mod = obj.modifiers.new(name="Mirror", type='MIRROR')
    mirror_mod.use_axis = [False, False, False]

    mirror_mod.use_axis[axis_idx] = True
    mirror_mod.use_bisect_flip_axis[axis_idx] = is_neg
    mirror_mod.use_bisect_axis[axis_idx] = True

    mirror_mod.mirror_object = _mirror_object
    mirror_mod.show_expanded = False


def _create_empty_mirror_object(context, location, orientation=(0.0, 0.0, 0.0)):
    '''Create an empty object at the given location and orientation for use as mirror_object'''

    empty = bpy.data.objects.new("RotorMirrorPivot", None)
    empty.empty_display_type = 'PLAIN_AXES'
    empty.location = location
    empty.rotation_euler = orientation
    context.collection.objects.link(empty)
    return empty


def _bisect_object(obj, axis_idx, pivot, orientation, context):
    """Bisect a single object using bmesh.ops.bisect_plane without changing modes"""

    if obj.type != 'MESH':
        return

    # Get the bisect plane normal vector
    normal = Vector((0, 0, 0))
    normal[axis_idx] = 1.0

    # Get the pivot point
    if pivot == 'WORLD':
        pivot_point = Vector((0, 0, 0))
    elif pivot == 'ACTIVE' and context.active_object:
        pivot_point = context.active_object.location.copy()
    elif pivot == 'INDIVIDUAL':
        pivot_point = obj.location.copy()
    elif pivot == 'CURSOR':
        pivot_point = context.scene.cursor.location.copy()
    else:
        pivot_point = Vector((0, 0, 0))

    # Transform normal based on orientation
    obj_normal = normal.copy()
    if orientation == 'LOCAL':
        if pivot == 'ACTIVE' and context.active_object:
            # Use active object's rotation to transform the normal
            rot_mat = context.active_object.rotation_euler.to_matrix()
            obj_normal = rot_mat @ obj_normal
        elif pivot == 'INDIVIDUAL':
            # Use this object's rotation to transform the normal
            rot_mat = obj.rotation_euler.to_matrix()
            obj_normal = rot_mat @ obj_normal
        elif pivot == 'WORLD':
            # When pivot is WORLD and orientation is LOCAL, use object's rotation
            rot_mat = obj.rotation_euler.to_matrix()
            obj_normal = rot_mat @ obj_normal
        elif pivot == 'CURSOR':
            # When pivot is CURSOR and orientation is LOCAL, use object's rotation
            rot_mat = obj.rotation_euler.to_matrix()
            obj_normal = rot_mat @ obj_normal
    elif orientation == 'CURSOR':
        # Use cursor's rotation to transform the normal regardless of pivot
        rot_mat = context.scene.cursor.rotation_euler.to_matrix()
        obj_normal = rot_mat @ obj_normal

    # Create new bmesh from mesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Transform pivot point to object's local space
    world_to_local = obj.matrix_world.inverted()
    local_pivot = world_to_local @ pivot_point

    # Transform normal to object's local space
    local_normal = world_to_local.to_3x3() @ obj_normal
    local_normal.normalize()

    # Perform bisect operation
    bmesh.ops.bisect_plane(
        bm,
        geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
        plane_co=local_pivot,
        plane_no=local_normal,
        clear_inner=True,
        clear_outer=False
    )

    # Update mesh and free bmesh
    bm.to_mesh(obj.data)
    bm.free()

    # Update object
    obj.data.update()


types_classes = (
    ROTOR_PG_MirrorObjectItem,
    ROTOR_PG_MirrorCollectionItem,
)

classes = (
    ROTOR_UL_MirrorObjectList,
    ROTOR_OT_SetMirrorAxis,
    ROTOR_OT_AddMirrorAxis,
    ROTOR_OT_FallbackTool,
    ROTOR_OT_AddMirrorCollection,
)
