import bpy
from ..utils import addon
from mathutils import Matrix, Vector


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

    def execute(self, context):
        axis_map = {'X': 0, 'Y': 1, 'Z': 2}
        axis_idx = axis_map[self.axis]
        is_neg = self.sign == 'NEG'

        active_object = context.active_object
        pref = addon.pref().tools.mirror
        pivot = pref.pivot
        orientation = pref.orientation


        def toggle_axis(use_axis, use_bisect_flip, use_bisect, axis_idx, is_neg):
            # State: (use_axis, use_bisect_flip, is_neg)
            # Value: (new_use_axis, new_use_bisect_flip)

            # Transition table schema:
            # Each key is a tuple: (use_axis, use_bisect_flip, is_neg)
            #   use_axis:         Is the mirror axis currently enabled? (bool)
            #   use_bisect_flip:  Is bisect flip enabled for this axis? (bool)
            #   is_neg:           Are we toggling the negative direction? (bool)
            #
            # Each value is a tuple: (new_use_axis, new_use_bisect_flip)
            #   new_use_axis:         New value for use_axis after toggle
            #   new_use_bisect_flip:  New value for use_bisect_flip after toggle
            #
            # Table summary:
            # | use_axis | use_bisect_flip | is_neg | new_use_axis | new_use_bisect_flip |
            # |----------|-----------------|--------|--------------|---------------------|
            # |  False   |     False       | False  |    True      |      False          |
            # |  False   |     False       | True   |    True      |      True           |
            # |  True    |     False       | False  |    False     |      False          |
            # |  True    |     False       | True   |    True      |      True           |
            # |  True    |     True        | False  |    True      |      False          |
            # |  True    |     True        | True   |    False     |      False          |


            transitions = {
                (False, False, False): (True, False),
                (False, False, True):  (True, True),
                (True, False, False):  (False, False),
                (True, False, True):   (True, True),
                (True, True, False):   (True, False),
                (True, True, True):    (False, False),
            }
            key = (use_axis[axis_idx], use_bisect_flip[axis_idx], is_neg)
            new_axis, new_bisect_flip = transitions[key]
            use_axis[axis_idx] = new_axis
            use_bisect_flip[axis_idx] = new_bisect_flip
            use_bisect[axis_idx] = True

        mirror_mod = next((m for m in reversed(active_object.modifiers) if m.type == 'MIRROR'), None)
        if mirror_mod is None:
            mirror_object, individual = _get_mirror_object(context, active_object, pivot, orientation)

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            # Find existing mirror modifier, or create one
            mirror_mod = next((m for m in reversed(obj.modifiers) if m.type == 'MIRROR'), None)
            if mirror_mod is None:
                _create_mirror_modifier(context, obj, mirror_object, individual, axis_idx, is_neg)
                continue

            # Set up axis and bisect options
            use_axis = mirror_mod.use_axis
            use_bisect_flip = mirror_mod.use_bisect_flip_axis
            use_bisect = mirror_mod.use_bisect_axis

            toggle_axis(use_axis, use_bisect_flip, use_bisect, axis_idx, is_neg)


        return {'FINISHED'}


class ROTOR_OT_AddMirrorAxis(bpy.types.Operator):
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

    def execute(self, context):
        axis_map = {'X': 0, 'Y': 1, 'Z': 2}
        axis_idx = axis_map[self.axis]
        is_neg = self.sign == 'NEG'

        active_object = context.active_object
        pref = addon.pref().tools.mirror
        pivot = pref.pivot
        orientation = pref.orientation

        mirror_object, individual = _get_mirror_object(context, active_object, pivot, orientation)

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            if obj.modifiers and obj.modifiers[-1].type == 'MIRROR':
                continue

            _create_mirror_modifier(context, obj, mirror_object, individual, axis_idx, is_neg)

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

    def execute(self, context):
        axis_map = {'X': 0, 'Y': 1, 'Z': 2}
        axis_idx = axis_map[self.axis]
        is_neg = self.sign == 'NEG'

        # Get mirror tool preferences
        pref = addon.pref().tools.mirror
        pivot = pref.pivot
        orientation = pref.orientation

        # Gather all unique collections from selected objects
        selected_objs = context.selected_objects
        collections = set()
        for obj in selected_objs:
            for col in getattr(obj, 'users_collection', []):
                # Ignore master collection and hidden/internal ones
                if not col.library and col.name != 'Scene Collection':
                    collections.add(col)

        # Avoid double instancing
        created = set()
        for col in collections:
            if col in created:
                continue
            created.add(col)

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
            # For WORLD or GLOBAL, rot_mat stays None

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

        return {'FINISHED'}


def _get_mirror_object(context, obj, pivot, orientation):
    mirror_object = None
    individual = False

    match (pivot, orientation):
        case ('ACTIVE', 'LOCAL'):
            mirror_object = obj
        case ('ACTIVE', 'GLOBAL'):
            mirror_object = _create_empty_mirror_object(context, obj.location)
        case ('INDIVIDUAL', 'LOCAL'):
            mirror_object = None
        case ('INDIVIDUAL', 'GLOBAL'):
            individual = True
        case ('WORLD', 'LOCAL'):
            mirror_object = _create_empty_mirror_object(context, (0.0, 0.0, 0.0), orientation=obj.rotation_euler)
        case ('WORLD', 'GLOBAL'):
            mirror_object = _create_empty_mirror_object(context, (0.0, 0.0, 0.0))

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



def _create_empty_mirror_object(context, location, orientation=(0.0, 0.0, 0.0)):
    '''Create an empty object at the given location and orientation for use as mirror_object'''

    empty = bpy.data.objects.new("RotorMirrorPivot", None)
    empty.empty_display_type = 'PLAIN_AXES'
    empty.location = location
    empty.rotation_euler = orientation
    context.collection.objects.link(empty)
    return empty


classes = (
    ROTOR_OT_SetMirrorAxis,
    ROTOR_OT_AddMirrorAxis,
    ROTOR_OT_AddMirrorCollection,
)
