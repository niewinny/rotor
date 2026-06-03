import bpy
from .mirror_utils import (
    MIRROR_AXIS_TRANSITIONS,
    compute_mirror_xform,
    create_empty_mirror_object,
)


# Integration with the Chisel extension (SDF modeling). Chisel objects are
# regular MESH objects carrying an `obj.chisel` property group; their mirror
# is a custom SDF modifier item, not a Blender MIRROR modifier. All
# chisel-touching code lives here — chisel is never imported by module name
# (extensions live under the bl_ext.* namespace), detection is purely via the
# registered `chisel` object property, so everything degrades cleanly when
# chisel is disabled.

MIRROR_AXIS_PROPS = ("mirror_x", "mirror_y", "mirror_z")
FLIP_AXIS_PROPS = ("flip_x", "flip_y", "flip_z")


def is_chisel_object(obj):
    """True if obj is a Chisel SDF object (chisel enabled + marked is_sdf)"""
    chisel = getattr(obj, "chisel", None)
    if chisel is None:
        return False
    try:
        return bool(chisel.primitive.is_sdf)
    except (AttributeError, ReferenceError, RuntimeError):
        return False


def get_chisel_mirror_item(obj):
    """Return (item, index) of the last chisel MIRROR item, or (None, -1).

    The last MIRROR item is the chisel equivalent of rotor's pinned
    Blender mirror modifier.
    """
    items = obj.chisel.modifiers.items
    for i in range(len(items) - 1, -1, -1):
        if items[i].modifier_type == "MIRROR":
            return items[i], i
    return None, -1


def chisel_axis_state(item):
    """Return (use_axis, use_flip) lists matching Blender mirror modifier
    use_axis / use_bisect_flip_axis semantics."""
    use_axis = [getattr(item, prop) for prop in MIRROR_AXIS_PROPS]
    use_flip = [getattr(item, prop) for prop in FLIP_AXIS_PROPS]
    return use_axis, use_flip


def toggle_chisel_axis(item, axis_idx, is_neg):
    """Toggle one axis on a chisel mirror item using the shared state
    transition table. Returns True if any axis remains enabled.

    Chisel mirror props have update callbacks that handle cache
    invalidation, so direct writes are safe. Chisel mirror inherently
    bisects — there is no use_bisect analog to set.
    """
    use_axis, use_flip = chisel_axis_state(item)
    key = (use_axis[axis_idx], use_flip[axis_idx], is_neg)
    new_axis, new_flip = MIRROR_AXIS_TRANSITIONS[key]
    # Write only on change — every write fires chisel's invalidation callback
    if new_axis != use_axis[axis_idx]:
        setattr(item, MIRROR_AXIS_PROPS[axis_idx], new_axis)
    if new_flip != use_flip[axis_idx]:
        setattr(item, FLIP_AXIS_PROPS[axis_idx], new_flip)
    use_axis[axis_idx] = new_axis
    return any(use_axis)


def add_chisel_mirror(context, obj, axis_idx, is_neg, mirror_object, individual):
    """Add a new chisel mirror item on obj via chisel's operator (which
    handles cache invalidation + proxy-mesh bookkeeping), then configure
    sign and mirror origin to match rotor's pivot/orientation."""

    axis = ("X", "Y", "Z")[axis_idx]
    # Scope to a single object so the operator takes its self-mirror branch
    with context.temp_override(active_object=obj, selected_objects=[obj]):
        bpy.ops.chisel.add_mirror_selected(axis=axis)

    # The operator points active_index at the new item (it may be inserted
    # before chisel's pinned block, so don't search for the last item)
    items = obj.chisel.modifiers.items
    index = obj.chisel.modifiers.active_index
    if not (0 <= index < len(items)) or items[index].modifier_type != "MIRROR":
        return
    item = items[index]

    if is_neg:
        setattr(item, FLIP_AXIS_PROPS[axis_idx], True)

    # Resolve mirror origin with the same rules as create_mirror_modifier.
    # chisel's mirror_origin matches Blender's mirror_object semantics
    # (target's local axes + position, None = own origin). The individual
    # case needs the same identity-rotation empty as the mesh path —
    # mirror_origin=None would use the object's own (possibly rotated) axes.
    _mirror_object = mirror_object
    if mirror_object == obj:
        _mirror_object = None
    if individual:
        _mirror_object = create_empty_mirror_object(context, obj.location)
    if item.mirror_origin != _mirror_object:
        item.mirror_origin = _mirror_object


def remove_chisel_mirror(context, obj, index):
    """Remove the chisel mirror item at index via chisel's operator"""
    with context.temp_override(active_object=obj):
        bpy.ops.chisel.remove_modifier(index=index)


def create_chisel_real_mirror(context, obj, axis_idx):
    """Duplicate a chisel object chisel-style: shared mesh data, flipped
    across the mirror plane, marked as an instance of the original.

    Unlike create_real_mirror there is no data copy and no reverse_faces —
    the SDF engine regenerates the proxy mesh from the shared base, and
    flipping winding on shared data would corrupt the original.
    """
    new_obj = obj.copy()
    new_obj.data = obj.data  # SHARED — chisel instances share the base mesh

    # Link to same collections
    for col in obj.users_collection:
        col.objects.link(new_obj)

    mirror_xform = compute_mirror_xform(context, obj, axis_idx)
    new_obj.matrix_world = mirror_xform @ obj.matrix_world

    # Set instance_of property for chisel's instancing support
    if hasattr(new_obj, "chisel") and hasattr(new_obj.chisel, "instance_of"):
        new_obj.chisel.instance_of = obj

    return new_obj
