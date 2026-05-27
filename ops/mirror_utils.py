import bpy
import bmesh
from mathutils import Euler, Matrix, Vector
from ..utils import addon


# Mirror axis state transition table
# Key: (use_axis, use_bisect_flip, is_neg)
# Value: (new_use_axis, new_use_bisect_flip)
MIRROR_AXIS_TRANSITIONS = {
    (False, False, False): (True, False),  # Enable positive
    (False, False, True): (True, True),  # Enable negative
    (True, False, False): (False, False),  # Disable from positive
    (True, False, True): (True, True),  # Switch to negative
    (True, True, False): (True, False),  # Switch to positive
    (True, True, True): (False, False),  # Disable from negative
}


def toggle_axis(use_axis, use_bisect_flip, use_bisect, axis_idx, is_neg):
    # Apply transition based on current state
    key = (use_axis[axis_idx], use_bisect_flip[axis_idx], is_neg)
    new_axis, new_bisect_flip = MIRROR_AXIS_TRANSITIONS[key]
    use_axis[axis_idx] = new_axis
    use_bisect_flip[axis_idx] = new_bisect_flip
    use_bisect[axis_idx] = True


def get_mirror_object(context, obj, pivot, orientation):
    mirror_object = None
    individual = False

    match (pivot, orientation):
        case ("ACTIVE", "LOCAL"):
            mirror_object = obj
        case ("ACTIVE", "GLOBAL"):
            mirror_object = create_empty_mirror_object(context, obj.location)
        case ("ACTIVE", "CURSOR"):
            mirror_object = create_empty_mirror_object(
                context, obj.location, orientation=context.scene.cursor.rotation_euler
            )
        case ("INDIVIDUAL", "LOCAL"):
            mirror_object = None
        case ("INDIVIDUAL", "GLOBAL"):
            individual = True
        case ("INDIVIDUAL", "CURSOR"):
            individual = True
        case ("WORLD", "LOCAL"):
            mirror_object = create_empty_mirror_object(
                context, (0.0, 0.0, 0.0), orientation=obj.rotation_euler
            )
        case ("WORLD", "GLOBAL"):
            mirror_object = create_empty_mirror_object(context, (0.0, 0.0, 0.0))
        case ("WORLD", "CURSOR"):
            mirror_object = create_empty_mirror_object(
                context,
                (0.0, 0.0, 0.0),
                orientation=context.scene.cursor.rotation_euler,
            )
        case ("CURSOR", "LOCAL"):
            mirror_object = create_empty_mirror_object(
                context, context.scene.cursor.location, orientation=obj.rotation_euler
            )
        case ("CURSOR", "GLOBAL"):
            mirror_object = create_empty_mirror_object(
                context, context.scene.cursor.location
            )
        case ("CURSOR", "CURSOR"):
            mirror_object = create_empty_mirror_object(
                context,
                context.scene.cursor.location,
                orientation=context.scene.cursor.rotation_euler,
            )
        case ("CUSTOM", orient):
            pref = addon.pref().tools.mirror
            loc = Vector(pref.custom_location)
            if orient == "LOCAL":
                rot = obj.rotation_euler
            elif orient == "CURSOR":
                rot = context.scene.cursor.rotation_euler
            elif orient == "CUSTOM":
                rot = pref.custom_rotation
            else:  # GLOBAL
                rot = (0.0, 0.0, 0.0)
            mirror_object = create_empty_mirror_object(context, loc, orientation=rot)
        case (piv, "CUSTOM"):
            pref = addon.pref().tools.mirror
            if piv == "WORLD":
                loc = Vector((0.0, 0.0, 0.0))
            elif piv == "CURSOR":
                loc = context.scene.cursor.location.copy()
            else:  # ACTIVE or INDIVIDUAL -> object origin
                loc = obj.location.copy()
            mirror_object = create_empty_mirror_object(
                context, loc, orientation=pref.custom_rotation
            )

    return mirror_object, individual


def create_mirror_modifier(context, obj, mirror_object, individual, axis_idx, is_neg):
    """Create a mirror modifier for the given object"""

    _mirror_object = mirror_object

    if mirror_object == obj:
        _mirror_object = None

    if individual:
        _mirror_object = create_empty_mirror_object(context, obj.location)

    mirror_mod = obj.modifiers.new(name="Mirror", type="MIRROR")
    mirror_mod.use_axis = [False, False, False]

    mirror_mod.use_axis[axis_idx] = True
    mirror_mod.use_bisect_flip_axis[axis_idx] = is_neg
    mirror_mod.use_bisect_axis[axis_idx] = True

    mirror_mod.mirror_object = _mirror_object
    mirror_mod.show_expanded = False

    # Apply enabled properties from tool preferences
    pref = addon.pref().tools.mirror

    # Clipping & Merge
    if pref.apply_use_clip:
        mirror_mod.use_clip = pref.use_clip

    if pref.apply_use_mirror_merge:
        mirror_mod.use_mirror_merge = pref.use_mirror_merge

    if pref.apply_merge_threshold:
        mirror_mod.merge_threshold = pref.merge_threshold

    if pref.apply_bisect_threshold:
        mirror_mod.bisect_threshold = pref.bisect_threshold

    # UV Settings
    if pref.apply_use_mirror_u:
        mirror_mod.use_mirror_u = pref.use_mirror_u

    if pref.apply_use_mirror_v:
        mirror_mod.use_mirror_v = pref.use_mirror_v

    if pref.apply_mirror_offset_u:
        mirror_mod.mirror_offset_u = pref.mirror_offset_u

    if pref.apply_mirror_offset_v:
        mirror_mod.mirror_offset_v = pref.mirror_offset_v

    if pref.apply_offset_u:
        mirror_mod.offset_u = pref.offset_u

    if pref.apply_offset_v:
        mirror_mod.offset_v = pref.offset_v

    # Other Settings
    if pref.apply_use_mirror_vertex_groups:
        mirror_mod.use_mirror_vertex_groups = pref.use_mirror_vertex_groups

    if pref.apply_use_mirror_udim:
        mirror_mod.use_mirror_udim = pref.use_mirror_udim


def create_empty_mirror_object(context, location, orientation=(0.0, 0.0, 0.0)):
    """Create an empty object at the given location and orientation for use as mirror_object"""

    pref = addon.pref().tools.mirror

    empty = bpy.data.objects.new("RotorMirrorPivot", None)
    empty.empty_display_type = pref.empty_display_type
    empty.empty_display_size = pref.empty_display_size
    empty.location = location
    empty.rotation_euler = orientation
    context.collection.objects.link(empty)
    return empty


def bisect_object(obj, axis_idx, pivot, orientation, context, is_neg=False):
    """Bisect a single object using bmesh.ops.bisect_plane without changing modes"""

    if obj.type != "MESH":
        return

    # Get the bisect plane normal vector
    normal = Vector((0, 0, 0))
    normal[axis_idx] = -1.0 if is_neg else 1.0

    # Get the pivot point
    if pivot == "WORLD":
        pivot_point = Vector((0, 0, 0))
    elif pivot == "ACTIVE" and context.active_object:
        pivot_point = context.active_object.location.copy()
    elif pivot == "INDIVIDUAL":
        pivot_point = obj.location.copy()
    elif pivot == "CURSOR":
        pivot_point = context.scene.cursor.location.copy()
    elif pivot == "CUSTOM":
        pivot_point = Vector(addon.pref().tools.mirror.custom_location)
    else:
        pivot_point = Vector((0, 0, 0))

    # Transform normal based on orientation
    obj_normal = normal.copy()
    if orientation == "LOCAL":
        if pivot == "ACTIVE" and context.active_object:
            # Use active object's rotation to transform the normal
            rot_mat = context.active_object.rotation_euler.to_matrix()
            obj_normal = rot_mat @ obj_normal
        elif pivot == "INDIVIDUAL":
            # Use this object's rotation to transform the normal
            rot_mat = obj.rotation_euler.to_matrix()
            obj_normal = rot_mat @ obj_normal
        elif pivot == "WORLD":
            # When pivot is WORLD and orientation is LOCAL, use object's rotation
            rot_mat = obj.rotation_euler.to_matrix()
            obj_normal = rot_mat @ obj_normal
        elif pivot == "CURSOR":
            # When pivot is CURSOR and orientation is LOCAL, use object's rotation
            rot_mat = obj.rotation_euler.to_matrix()
            obj_normal = rot_mat @ obj_normal
    elif orientation == "CURSOR":
        # Use cursor's rotation to transform the normal regardless of pivot
        rot_mat = context.scene.cursor.rotation_euler.to_matrix()
        obj_normal = rot_mat @ obj_normal
    elif orientation == "CUSTOM":
        # Use the custom orientation to transform the normal regardless of pivot
        rot_mat = Euler(addon.pref().tools.mirror.custom_rotation, "XYZ").to_matrix()
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
        clear_outer=False,
    )

    # Update mesh and free bmesh
    bm.to_mesh(obj.data)
    bm.free()

    # Update object
    obj.data.update()


def create_real_mirror(context, obj, axis_idx, is_neg):
    """Duplicate object + mesh and flip across the mirror axis.

    Returns the new object or None if the object type is unsupported.
    """
    pref = addon.pref().tools.mirror
    pivot = pref.pivot
    orientation = pref.orientation

    # 1. Duplicate object and mesh data
    new_obj = obj.copy()
    if obj.data:
        new_obj.data = obj.data.copy()

    # Link to same collections
    for col in obj.users_collection:
        col.objects.link(new_obj)

    # 2. Build scale matrix with -1 on mirror axis
    scale_vec = [1.0, 1.0, 1.0]
    scale_vec[axis_idx] = -1.0
    mirror_mat = (
        Matrix.Scale(scale_vec[0], 4, Vector((1, 0, 0)))
        @ Matrix.Scale(scale_vec[1], 4, Vector((0, 1, 0)))
        @ Matrix.Scale(scale_vec[2], 4, Vector((0, 0, 1)))
    )

    # 3. Compute pivot point
    if pivot == "WORLD":
        pivot_point = Vector((0, 0, 0))
    elif pivot == "ACTIVE" and context.active_object:
        pivot_point = context.active_object.location.copy()
    elif pivot == "INDIVIDUAL":
        pivot_point = obj.location.copy()
    elif pivot == "CURSOR":
        pivot_point = context.scene.cursor.location.copy()
    elif pivot == "CUSTOM":
        pivot_point = Vector(addon.pref().tools.mirror.custom_location)
    else:
        pivot_point = Vector((0, 0, 0))

    # 4. Compute rotation from orientation
    rot_mat = None
    if orientation == "LOCAL":
        if pivot == "ACTIVE" and context.active_object:
            rot_mat = context.active_object.rotation_euler.to_matrix().to_4x4()
        elif pivot == "INDIVIDUAL":
            rot_mat = obj.rotation_euler.to_matrix().to_4x4()
        elif pivot in ("WORLD", "CURSOR", "CUSTOM"):
            rot_mat = obj.rotation_euler.to_matrix().to_4x4()
    elif orientation == "CURSOR":
        rot_mat = context.scene.cursor.rotation_euler.to_matrix().to_4x4()
    elif orientation == "CUSTOM":
        rot_mat = Euler(addon.pref().tools.mirror.custom_rotation, "XYZ").to_matrix().to_4x4()

    # 5. Compose mirror_xform = T @ R @ S @ R_inv @ T_inv
    T = Matrix.Translation(pivot_point)
    T_inv = Matrix.Translation(-pivot_point)
    S = mirror_mat
    if rot_mat is not None:
        R = rot_mat
        R_inv = rot_mat.inverted()
        mirror_xform = T @ R @ S @ R_inv @ T_inv
    else:
        mirror_xform = T @ S @ T_inv

    # 6. Apply transform
    new_obj.matrix_world = mirror_xform @ obj.matrix_world

    # 7. Fix normals — negative scale inverts face winding
    if new_obj.type == "MESH" and new_obj.data:
        bm = bmesh.new()
        bm.from_mesh(new_obj.data)
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(new_obj.data)
        bm.free()
        new_obj.data.update()

    return new_obj


def execute_real_mirror(operator, context, axis_idx, is_neg, enabled_objects):
    """Shared helper for real-mirror mode used by both set and add operators.

    Handles bisect, loop over objects, selection update, and report.
    Returns {'FINISHED'} or {'CANCELLED'}.
    """
    pref = addon.pref().tools.mirror
    pivot = pref.pivot
    orientation = pref.orientation

    new_objects = []
    for obj in enabled_objects:
        if pref.bisect:
            bisect_object(obj, axis_idx, pivot, orientation, context, is_neg)

        new_obj = create_real_mirror(context, obj, axis_idx, is_neg)
        if new_obj:
            new_objects.append(new_obj)

    if not new_objects:
        operator.report({"WARNING"}, "No objects were mirrored.")
        return {"CANCELLED"}

    # Update selection: deselect originals, select new objects
    for obj in enabled_objects:
        obj.select_set(False)
    for new_obj in new_objects:
        new_obj.select_set(True)
    context.view_layer.objects.active = new_objects[0]

    operator.report({"INFO"}, f"Created {len(new_objects)} mirrored copies.")

    # Tool fallback
    last_tool = context.scene.rotor.ops.last_tool
    if pref.tool_fallback and last_tool:
        current_tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        )
        if current_tool and current_tool.idname == "mirror.mirror_tool":
            try:
                bpy.ops.wm.tool_set_by_id(name=last_tool)
                context.scene.rotor.ops.last_tool = ""
            except Exception:
                pass

    return {"FINISHED"}
