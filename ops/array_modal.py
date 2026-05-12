import os
from math import pi

import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import intersect_line_line, intersect_line_plane
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

from ..utils import addon, infobar
from ..utils.operator import safe
from ..utils.scene import ray_cast
from ..shaders import handle
from ..shaders.draw import AXIS_DATA


def _snap_view(origin, region, rv3d, mouse_pos):
    """Project mouse onto a plane at origin facing the view."""
    ray_origin = region_2d_to_origin_3d(region, rv3d, mouse_pos)
    ray_dir = region_2d_to_vector_3d(region, rv3d, mouse_pos)

    if rv3d.is_perspective:
        view_normal = (ray_origin - origin).normalized()
    else:
        view_normal = -rv3d.view_matrix.inverted().col[2].to_3d().normalized()

    point = intersect_line_plane(
        ray_origin, ray_origin + ray_dir, origin, view_normal,
    )
    return point


def _raycast(context, mouse_pos, exclude):
    """Shared raycast helper that excludes the source object."""
    return ray_cast.visible(
        context, (mouse_pos.x, mouse_pos.y), exclude=exclude
    )


def _snap_origin(context, mouse_pos, exclude):
    """Raycast and snap to the hit object's origin."""
    ray = _raycast(context, mouse_pos, exclude)
    if ray.hit and ray.obj:
        return ray.obj.matrix_world.translation.copy()
    return None


def _snap_face(context, mouse_pos, exclude):
    """Raycast and snap to the hit point on the face."""
    ray = _raycast(context, mouse_pos, exclude)
    if ray.hit:
        return ray.location.copy()
    return None


def _snap_vertex(context, mouse_pos, exclude):
    """Raycast to face, then find closest vertex."""
    ray = _raycast(context, mouse_pos, exclude)
    if not ray.hit or not ray.obj:
        return None

    obj = ray.obj
    mesh = obj.data
    mat = obj.matrix_world

    if ray.index < 0 or ray.index >= len(mesh.polygons):
        return None

    poly = mesh.polygons[ray.index]
    hit_loc = ray.location

    closest_dist = float("inf")
    closest_point = None
    for vi in poly.vertices:
        world_co = mat @ mesh.vertices[vi].co
        dist = (world_co - hit_loc).length_squared
        if dist < closest_dist:
            closest_dist = dist
            closest_point = world_co

    return closest_point


def _snap_edge(context, mouse_pos, exclude):
    """Raycast to face, then find closest edge point."""
    ray = _raycast(context, mouse_pos, exclude)
    if not ray.hit or not ray.obj:
        return None

    obj = ray.obj
    mesh = obj.data
    mat = obj.matrix_world

    if ray.index < 0 or ray.index >= len(mesh.polygons):
        return None

    poly = mesh.polygons[ray.index]
    hit_loc = ray.location
    verts = poly.vertices

    closest_dist = float("inf")
    closest_point = None
    for i in range(len(verts)):
        a = mat @ mesh.vertices[verts[i]].co
        b = mat @ mesh.vertices[verts[(i + 1) % len(verts)]].co
        point = _closest_point_on_segment(hit_loc, a, b)
        dist = (point - hit_loc).length_squared
        if dist < closest_dist:
            closest_dist = dist
            closest_point = point

    return closest_point


def _snap_edge_center(context, mouse_pos, exclude):
    """Raycast to face, find closest edge, return its midpoint."""
    ray = _raycast(context, mouse_pos, exclude)
    if not ray.hit or not ray.obj:
        return None

    obj = ray.obj
    mesh = obj.data
    mat = obj.matrix_world

    if ray.index < 0 or ray.index >= len(mesh.polygons):
        return None

    poly = mesh.polygons[ray.index]
    hit_loc = ray.location
    verts = poly.vertices

    closest_dist = float("inf")
    closest_mid = None
    for i in range(len(verts)):
        a = mat @ mesh.vertices[verts[i]].co
        b = mat @ mesh.vertices[verts[(i + 1) % len(verts)]].co
        mid = (a + b) * 0.5
        point = _closest_point_on_segment(hit_loc, a, b)
        dist = (point - hit_loc).length_squared
        if dist < closest_dist:
            closest_dist = dist
            closest_mid = mid

    return closest_mid


def _snap_face_center(context, mouse_pos, exclude):
    """Raycast and snap to the hit face's center."""
    ray = _raycast(context, mouse_pos, exclude)
    if not ray.hit or not ray.obj:
        return None

    obj = ray.obj
    mesh = obj.data
    mat = obj.matrix_world

    if ray.index < 0 or ray.index >= len(mesh.polygons):
        return None

    poly = mesh.polygons[ray.index]
    return mat @ poly.center


def _closest_point_on_segment(point, a, b):
    """Return the closest point on segment a-b to point."""
    ab = b - a
    t = (point - a).dot(ab) / ab.dot(ab)
    t = max(0.0, min(1.0, t))
    return a + ab * t


_SNAP_FUNCTIONS = {
    "ORIGIN": _snap_origin,
    "FACE": _snap_face,
    "VERTEX": _snap_vertex,
    "EDGE": _snap_edge,
    "EDGE_CENTER": _snap_edge_center,
    "FACE_CENTER": _snap_face_center,
}

_MODE_CYCLE = ("LINEAR", "CIRCLE")
_PIVOT_CYCLE = ("INCREMENT", "GRID", "ORIGIN", "FACE", "VERTEX", "EDGE", "EDGE_CENTER", "FACE_CENTER")
_ORIENTATION_CYCLE = ("GLOBAL", "LOCAL")


def _compute_circle_axis(axis_x, axis_y, axis_z, orientation, local_rot, context=None):
    """Return world-space rotation axis for circle mode.

    - 1 axis  → perpendicular to that axis (cross with view), so the
                 object stays on the circle and the circle contains the axis
    - 2 axes  → rotate around the disabled axis (normal to the plane)
    - 0 or 3  → fall back to view normal or world Z
    """
    axes_enabled = [axis_x, axis_y, axis_z]
    num_axes = sum(axes_enabled)
    if num_axes == 0 or num_axes == 3:
        if context:
            rv3d = context.region_data
            if rv3d:
                return -rv3d.view_matrix.inverted().col[2].to_3d().normalized()
        return Vector((0, 0, 1))
    r = local_rot if orientation == "LOCAL" else Matrix.Identity(3)
    axis_names = ["x", "y", "z"]
    if num_axes == 1:
        idx = axes_enabled.index(True)
        face = (r @ AXIS_DATA[axis_names[idx]][0]).normalized()
        if context:
            rv3d = context.region_data
            if rv3d:
                view = -rv3d.view_matrix.inverted().col[2].to_3d().normalized()
                cross = face.cross(view)
                if cross.length > 1e-6:
                    return cross.normalized()
        return face.orthogonal().normalized()
    else:
        idx = axes_enabled.index(False)
    return (r @ AXIS_DATA[axis_names[idx]][0]).normalized()


def _resolve_face_direction(face_axis, orientation, local_rot, rot_axis):
    """Return world-space facing direction from face_axis enum, projected onto circle plane.

    Returns None if face_axis is "NONE".
    """
    if face_axis == "NONE":
        return None
    r = local_rot if orientation == "LOCAL" else Matrix.Identity(3)
    name = face_axis.lower()
    raw = (r @ AXIS_DATA[name][0]).normalized()
    projected = raw - rot_axis * raw.dot(rot_axis)
    if projected.length < 1e-6:
        return None
    return projected.normalized()


def _is_object_pointer(prop):
    """Return True if *prop* is a writable pointer to bpy.types.Object."""
    if prop.type != 'POINTER' or prop.is_readonly or not prop.fixed_type:
        return False
    return prop.fixed_type.bl_rna == bpy.types.Object.bl_rna


def _is_id_type(rna_struct):
    """Return True if *rna_struct* inherits from bpy.types.ID."""
    cur = rna_struct
    while cur:
        if cur.identifier == 'ID':
            return True
        cur = cur.base
    return False


def _swap_object_pointers(data, old_to_new):
    """Replace Object references on *data* via RNA and ID properties."""
    for prop in data.bl_rna.properties:
        if not _is_object_pointer(prop):
            continue
        ref = getattr(data, prop.identifier, None)
        if ref and ref in old_to_new:
            try:
                setattr(data, prop.identifier, old_to_new[ref])
            except Exception:
                pass
    try:
        for key in data.keys():
            try:
                val = data[key]
            except Exception:
                continue
            if isinstance(val, bpy.types.Object) and val in old_to_new:
                try:
                    data[key] = old_to_new[val]
                except Exception:
                    pass
    except (AttributeError, TypeError):
        pass


def _walk_and_swap(data, old_to_new, visited):
    """Recurse into non-ID sub-properties of *data* and swap Object refs."""
    try:
        key = data.as_pointer()
    except (AttributeError, RuntimeError):
        return
    if key in visited:
        return
    visited.add(key)

    _swap_object_pointers(data, old_to_new)

    for prop in data.bl_rna.properties:
        if prop.identifier == 'rna_type':
            continue
        if prop.type == 'POINTER' and prop.fixed_type:
            if prop.fixed_type.bl_rna == bpy.types.Object.bl_rna:
                continue
            if _is_id_type(prop.fixed_type.bl_rna):
                continue
            try:
                sub = getattr(data, prop.identifier)
                if sub is not None and hasattr(sub, 'bl_rna'):
                    _walk_and_swap(sub, old_to_new, visited)
            except Exception:
                pass
        elif prop.type == 'COLLECTION':
            try:
                for item in getattr(data, prop.identifier):
                    if hasattr(item, 'bl_rna'):
                        _walk_and_swap(item, old_to_new, visited)
            except Exception:
                pass


def _get_array_node_group():
    """Return the essentials Array geometry node group, loading it if needed."""
    existing = bpy.data.node_groups.get("Array")
    if existing and existing.type == 'GEOMETRY':
        return existing

    blend_path = os.path.join(
        bpy.utils.system_resource('DATAFILES'),
        "assets", "nodes", "geometry_nodes_essentials.blend",
    )
    if not os.path.exists(blend_path):
        return None

    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        if "Array" not in data_from.node_groups:
            return None
        data_to.node_groups = ["Array"]
    return bpy.data.node_groups.get("Array")


def _input_identifier_map(node_group):
    """Return {socket name: identifier} for INPUT sockets only."""
    ids = {}
    for item in node_group.interface.items_tree:
        if getattr(item, 'item_type', None) != 'SOCKET':
            continue
        if getattr(item, 'in_out', None) != 'INPUT':
            continue
        ids[item.name] = item.identifier
    return ids


def _set_gn_input(mod, identifier, value):
    """Set a Geometry Nodes modifier input by socket identifier.

    Uses the Blender 5.2+ ``mod.properties.inputs.<id>.value`` API when
    available, with a fallback to the older id-property subscript form.
    """
    if identifier is None:
        return
    props = getattr(mod, "properties", None)
    if props is not None:
        socket = getattr(props.inputs, identifier, None)
        if socket is None:
            return
        try:
            socket.value = value
        except Exception:
            pass
        return
    try:
        mod[identifier] = value
    except (TypeError, KeyError):
        pass


def _remap_references(copies, selection, context):
    """Remap inter-object references so duplicates point to each other."""
    if not copies:
        return
    from collections import defaultdict
    instances = defaultdict(list)
    for src, new, idx in copies:
        instances[idx].append((src, new))

    context.view_layer.update()

    for instance_copies in instances.values():
        old_to_new = {src: new for src, new in instance_copies}
        for src, new_obj in instance_copies:
            if src.parent and src.parent in old_to_new:
                new_obj.parent = old_to_new[src.parent]
            _walk_and_swap(new_obj, old_to_new, set())


class ROTOR_OT_ArrayModal(bpy.types.Operator):
    """Array object with visual guide"""

    bl_idname = "mirror.array_modal"
    bl_label = "Array"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    object_name: bpy.props.StringProperty(
        name="Object",
        description="Name of the object to duplicate",
    )
    count: bpy.props.IntProperty(
        name="Count",
        description="Number of duplicates",
        default=1,
        min=1,
    )
    dup_scale: bpy.props.FloatProperty(
        name="Scale",
        description="Scale factor for duplicates",
        default=1.0,
        min=0.01,
        max=10.0,
    )
    location: bpy.props.FloatVectorProperty(
        name="Location",
        description="Target placement point",
        subtype="XYZ",
    )
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[("LINEAR", "Linear", ""), ("CIRCLE", "Circle", "")],
        default="LINEAR",
    )
    axis_x: bpy.props.BoolProperty(name="X")
    axis_y: bpy.props.BoolProperty(name="Y")
    axis_z: bpy.props.BoolProperty(name="Z")
    double: bpy.props.BoolProperty(name="Double")
    align: bpy.props.BoolProperty(name="Align")
    face_axis: bpy.props.EnumProperty(
        name="Face",
        items=[("NONE", "None", ""), ("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")],
        default="NONE",
    )
    orientation: bpy.props.EnumProperty(
        name="Orientation",
        items=[("GLOBAL", "Global", ""), ("LOCAL", "Local", "")],
        default="GLOBAL",
    )

    def invoke(self, context, event):
        obj = bpy.data.objects.get(self.object_name) if self.object_name else None
        if not obj:
            obj = context.active_object
        if not obj:
            self.report({"WARNING"}, "No object found")
            return {"CANCELLED"}

        self._exclude = {obj}
        self._selection = [o for o in context.selected_objects]
        self._origin = obj.matrix_world.translation.copy()
        self._origins = [o.matrix_world.translation.copy() for o in self._selection]
        self._local_rot = obj.matrix_world.to_3x3().normalized()
        self._last_point = None
        self._guide = handle.Guide()
        self._guide.create(context)
        self._ghost = handle.Ghost()
        self._ghost.create(context, obj)
        infobar.draw(context, event, self._infobar, blank=True)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    @safe
    def modal(self, context, event):
        context.area.tag_redraw()
        infobar.draw(context, event, self._infobar, blank=True)
        dup = addon.pref().tools.array
        self._update_header(context, dup)

        changed = False

        if event.type in {"X", "Y", "Z"} and event.value == "PRESS":
            if event.ctrl:
                axis = event.type
                dup.face_axis = "NONE" if dup.face_axis == axis else axis
            else:
                attr = f"axis_{event.type.lower()}"
                setattr(dup, attr, not getattr(dup, attr))
            changed = True

        elif event.type == "N" and event.value == "PRESS":
            dup.axis_x = False
            dup.axis_y = False
            dup.axis_z = False
            changed = True

        elif event.type == "C" and event.value == "PRESS":
            cur = _MODE_CYCLE.index(dup.mode)
            dup.mode = _MODE_CYCLE[(cur + 1) % len(_MODE_CYCLE)]
            changed = True

        elif event.type == "O" and event.value == "PRESS":
            cur = _ORIENTATION_CYCLE.index(dup.snap.orientation)
            dup.snap.orientation = _ORIENTATION_CYCLE[(cur + 1) % len(_ORIENTATION_CYCLE)]
            changed = True

        elif event.type == "P" and event.value == "PRESS":
            cur = _PIVOT_CYCLE.index(dup.snap.pivot)
            dup.snap.pivot = _PIVOT_CYCLE[(cur + 1) % len(_PIVOT_CYCLE)]
            changed = True

        elif event.type in {"RIGHT_BRACKET", "WHEELUPMOUSE"} and event.value == "PRESS":
            dup.count += 1
            changed = True

        elif event.type in {"LEFT_BRACKET", "WHEELDOWNMOUSE"} and event.value == "PRESS":
            if dup.count > 1:
                dup.count -= 1
                changed = True

        elif event.type == "QUOTE" and event.value == "PRESS":
            step = 0.01 if event.shift else 0.1
            dup.scale = round(dup.scale + step, 2)
            changed = True

        elif event.type == "SEMI_COLON" and event.value == "PRESS":
            step = 0.01 if event.shift else 0.1
            dup.scale = max(0.01, round(dup.scale - step, 2))
            changed = True

        elif event.type == "D" and event.value == "PRESS":
            dup.double = not dup.double
            changed = True

        elif event.type == "A" and event.value == "PRESS":
            dup.align = not dup.align
            changed = True

        if changed:
            if self._last_point:
                self._update_preview(context, dup, self._last_point)
            return {"RUNNING_MODAL"}

        if event.type == "MOUSEMOVE":
            point = self._snap(context, event)
            if point:
                self._last_point = point
                self._update_preview(context, dup, point)

        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._cancel(context)
            return {"CANCELLED"}

        if ((event.type == "LEFTMOUSE" and event.value == "RELEASE")
                or (event.type in {"SPACE", "RET"} and event.value == "PRESS")):
            self._finish(context)
            return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def _infobar(self, layout, context, event):
        """Draw the infobar hotkeys for the duplicate modal."""
        factor = 4.0
        row = layout.row(align=True)

        row.label(text="", icon="MOUSE_MOVE")
        row.label(text="Place")
        row.separator(factor=factor)
        row.label(text="Confirm", icon="MOUSE_LMB")
        row.separator(factor=factor)
        row.label(text="Cancel", icon="MOUSE_RMB")
        row.separator(factor=factor)
        row.label(text="Mode", icon="EVENT_C")
        row.separator(factor=factor)
        row.label(text="Axis", icon="EVENT_X")
        row.separator(factor=factor)
        row.label(text="Clear Axis", icon="EVENT_N")
        row.separator(factor=factor)
        row.label(text="[ ]  Count")
        row.separator(factor=factor)
        row.label(text="; '  Scale")
        row.separator(factor=factor)
        row.label(text="Orientation", icon="EVENT_O")
        row.separator(factor=factor)
        row.label(text="Snap", icon="EVENT_P")
        row.separator(factor=factor)
        row.label(text="Double", icon="EVENT_D")
        row.separator(factor=factor)
        row.label(text="Align", icon="EVENT_A")
        row.separator(factor=factor)
        row.label(text="Ctrl+XYZ  Face Axis")
        row.separator(factor=factor)

    def _update_header(self, context, dup):
        """Update the header with live values."""
        axes = []
        if dup.axis_x:
            axes.append("X")
        if dup.axis_y:
            axes.append("Y")
        if dup.axis_z:
            axes.append("Z")
        axis_text = ", ".join(axes) if axes else "Free"

        parts = [
            f"Mode: {dup.mode.capitalize()}",
            f"Count: {dup.count}",
            f"Scale: {dup.scale:.2f}",
            f"Axis: {axis_text}",
            f"Orientation: {dup.snap.orientation.capitalize()}",
            f"Snap: {dup.snap.pivot.replace('_', ' ').capitalize()}",
        ]
        if dup.mode == "LINEAR" and dup.double:
            parts.append("Double: On")
        if dup.mode == "CIRCLE":
            if dup.align:
                parts.append("Align: On")
            face_text = dup.face_axis if dup.face_axis != "NONE" else "Auto"
            parts.append(f"Face: {face_text}")

        context.area.header_text_set(text="    ".join(parts))

    def _update_preview(self, context, dup, point):
        """Refresh guide and ghost preview for the given point."""
        rot = self._local_rot if dup.snap.orientation == "LOCAL" else None
        is_circle = dup.mode == "CIRCLE"
        circle_guide = is_circle
        self._guide.callback.update(
            self._origin, point,
            axis_x=dup.axis_x, axis_y=dup.axis_y, axis_z=dup.axis_z,
            orientation=rot,
            double=dup.double and not is_circle,
            circle=circle_guide,
        )
        self._ghost.callback.update(
            self._ghost_positions(point, dup, context)
        )

    def _snap_to_constraint(self, context, mouse):
        """Cast cursor ray onto the constraint plane/line defined by enabled axes."""
        dup = addon.pref().tools.array
        axes_enabled = [dup.axis_x, dup.axis_y, dup.axis_z]
        num_axes = sum(axes_enabled)
        is_circle = dup.mode == "CIRCLE"

        if num_axes == 0 or num_axes == 3:
            return None  # No constraint or all axes — use view plane

        region = context.region
        rv3d = context.region_data
        ray_origin = region_2d_to_origin_3d(region, rv3d, mouse)
        ray_dir = region_2d_to_vector_3d(region, rv3d, mouse)
        rot = self._local_rot if dup.snap.orientation == "LOCAL" else Matrix.Identity(3)
        axis_names = ["x", "y", "z"]

        if is_circle:
            if num_axes == 1:
                # 1 axis: constrain cursor along that axis
                enabled_idx = axes_enabled.index(True)
                axis_dir = rot @ AXIS_DATA[axis_names[enabled_idx]][0]
                result = intersect_line_line(
                    self._origin, self._origin + axis_dir,
                    ray_origin, ray_origin + ray_dir,
                )
                return result[0] if result else None
            else:
                # 2 axes: snap to the circle plane
                disabled_idx = axes_enabled.index(False)
                normal = rot @ AXIS_DATA[axis_names[disabled_idx]][0]
                return intersect_line_plane(
                    ray_origin, ray_origin + ray_dir, self._origin, normal,
                )
        else:
            if num_axes == 2:
                # Plane constraint: normal is the disabled axis
                disabled_idx = axes_enabled.index(False)
                normal = rot @ AXIS_DATA[axis_names[disabled_idx]][0]
                return intersect_line_plane(
                    ray_origin, ray_origin + ray_dir, self._origin, normal,
                )
            else:
                # Line constraint: closest point on axis to cursor ray
                enabled_idx = axes_enabled.index(True)
                axis_dir = rot @ AXIS_DATA[axis_names[enabled_idx]][0]
                result = intersect_line_line(
                    self._origin, self._origin + axis_dir,
                    ray_origin, ray_origin + ray_dir,
                )
                return result[0] if result else None

    def _snap(self, context, event):
        region = context.region
        rv3d = context.region_data
        mouse = Vector((event.mouse_region_x, event.mouse_region_y))

        use_snap = context.tool_settings.use_snap != event.ctrl
        pivot = addon.pref().tools.array.snap.pivot
        point = None

        if use_snap and pivot not in {"INCREMENT", "GRID"}:
            snap_fn = _SNAP_FUNCTIONS.get(pivot)
            point = snap_fn(context, mouse, self._exclude) if snap_fn else None

            # Raycast may deselect objects — restore selection
            for obj in self._selection:
                if not obj.select_get():
                    obj.select_set(True)

        if point is None:
            point = self._snap_to_constraint(context, mouse)

        if point is None:
            point = _snap_view(self._origin, region, rv3d, mouse)

        if use_snap and point:
            if pivot == "INCREMENT":
                point = self._snap_increment(context, point)
            elif pivot == "GRID":
                point = self._snap_grid(context, point)

        return point

    @staticmethod
    def _grid_step(context):
        overlay = context.space_data.overlay
        return overlay.grid_scale / overlay.grid_subdivisions

    def _snap_increment(self, context, point):
        """Snap the offset from origin to the nearest grid increment."""
        step = self._grid_step(context)
        offset = point - self._origin
        for i in range(3):
            offset[i] = round(offset[i] / step) * step
        return self._origin + offset

    @staticmethod
    def _snap_grid(context, point):
        """Snap the absolute position to the nearest grid line."""
        step = ROTOR_OT_ArrayModal._grid_step(context)
        snapped = point.copy()
        for i in range(3):
            snapped[i] = round(point[i] / step) * step
        return snapped

    def _ghost_offsets(self, point, dup):
        """Compute direction offsets from grabbed object's origin.

        Enabled axes define a constraint plane/line — the offset is projected
        onto the subspace spanned by the active axes.
        """
        diff = point - self._origin
        any_axis = dup.axis_x or dup.axis_y or dup.axis_z
        is_circle = dup.mode == "CIRCLE"
        factor = 1.0 if is_circle else (2.0 if dup.double else 1.0)
        if not any_axis:
            return [diff * factor]
        r = self._local_rot if dup.snap.orientation == "LOCAL" else Matrix.Identity(3)
        combined = Vector((0, 0, 0))
        for name, enabled in [("x", dup.axis_x), ("y", dup.axis_y), ("z", dup.axis_z)]:
            if enabled:
                d = r @ AXIS_DATA[name][0]
                combined += d * diff.dot(d)
        return [combined * factor]

    @staticmethod
    def _view_normal(context):
        rv3d = context.region_data
        return -rv3d.view_matrix.inverted().col[2].to_3d().normalized()

    def _circle_axis(self, dup, context):
        """Return a single rotation axis for circle mode."""
        return _compute_circle_axis(
            dup.axis_x, dup.axis_y, dup.axis_z,
            dup.snap.orientation, self._local_rot, context,
        )

    @staticmethod
    def _apply_circle_align(obj, angle, axis):
        """Rotate obj by *angle* around *axis*, composing with its current rotation."""
        circle_quat = Matrix.Rotation(angle, 3, axis).to_quaternion()
        mode = obj.rotation_mode
        if mode == 'QUATERNION':
            obj.rotation_quaternion = circle_quat @ obj.rotation_quaternion
        elif mode == 'AXIS_ANGLE':
            aa = obj.rotation_axis_angle
            base = Matrix.Rotation(aa[0], 3, Vector(aa[1:])).to_quaternion()
            result = circle_quat @ base
            ax, ang = result.to_axis_angle()
            obj.rotation_axis_angle = (ang, *ax)
        else:
            base = obj.rotation_euler.to_quaternion()
            result = circle_quat @ base
            obj.rotation_euler = result.to_euler(mode)

    def _ghost_positions(self, point, dup, context):
        """Compute ghost placements (position, scale, rotation) for current mode."""
        count = dup.count
        scale = dup.scale
        align = dup.align
        placements = []

        if dup.mode == "CIRCLE":
            diff = point - self._origin
            rot_axis = self._circle_axis(dup, context)
            face_dir = _resolve_face_direction(
                dup.face_axis, dup.snap.orientation, self._local_rot, rot_axis,
            )
            for org in self._origins:
                if face_dir is not None:
                    start = face_dir * diff.length / 2
                    center = org + diff / 2
                else:
                    center = org + diff
                    start = -diff
                for i in range(1, count + 1):
                    angle = 2 * pi * i / (count + 1)
                    rot = Matrix.Rotation(angle, 3, rot_axis)
                    pos = center + rot @ start
                    ghost_rot = rot if align else None
                    placements.append((pos, scale, ghost_rot))
        else:
            offsets = self._ghost_offsets(point, dup)
            any_axis = dup.axis_x or dup.axis_y or dup.axis_z
            for org in self._origins:
                for offset in offsets:
                    for i in range(1, count + 1):
                        t = i / count
                        s = 1.0 + (scale - 1.0) * t
                        pos = org + offset * t
                        placements.append((pos, s, None))
        return placements

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "count")
        layout.prop(self, "dup_scale")
        layout.prop(self, "align")
        col = layout.column(align=True)
        col.prop(self, "location")

    def execute(self, context):
        if addon.pref().tools.array.real:
            self._create_duplicates(context)
        else:
            self._create_gn_array(context)
        return {"FINISHED"}

    def _finish(self, context):
        """Copy modal state to operator properties, clean up, create duplicates."""
        context.area.header_text_set(text=None)
        infobar.remove(context)
        self._guide.remove()
        self._ghost.remove()
        if not self._last_point:
            context.area.tag_redraw()
            return

        dup = addon.pref().tools.array
        self.count = dup.count
        self.dup_scale = dup.scale
        self.location = self._last_point
        self.mode = dup.mode
        self.axis_x = dup.axis_x
        self.axis_y = dup.axis_y
        self.axis_z = dup.axis_z
        self.double = dup.double
        self.align = dup.align
        self.face_axis = dup.face_axis
        self.orientation = dup.snap.orientation

        if dup.real:
            self._create_duplicates(context)
        else:
            self._create_gn_array(context)
        context.area.tag_redraw()

    def _create_gn_array(self, context):
        """Create GN Array modifiers using the essentials Array node group."""
        obj = bpy.data.objects.get(self.object_name) if self.object_name else context.active_object
        if not obj:
            return

        array_group = _get_array_node_group()
        if not array_group:
            return

        selection = list(context.selected_objects)
        if not selection:
            selection = [obj]

        count = self.count
        origin = obj.matrix_world.translation.copy()
        local_rot = obj.matrix_world.to_3x3().normalized()
        point = Vector(self.location)
        diff = point - origin
        any_axis = self.axis_x or self.axis_y or self.axis_z
        is_circle = self.mode == "CIRCLE"
        factor = 2.0 if self.double else 1.0

        # Compute world-space offset for linear mode
        if not is_circle:
            if not any_axis:
                total_offset = diff * factor
            else:
                r = local_rot if self.orientation == "LOCAL" else Matrix.Identity(3)
                total_offset = Vector((0, 0, 0))
                for name, enabled in [("x", self.axis_x), ("y", self.axis_y), ("z", self.axis_z)]:
                    if enabled:
                        d = r @ AXIS_DATA[name][0]
                        total_offset += d * factor * diff.dot(d)
            step_offset = total_offset / count if count > 0 else total_offset

        ids = _input_identifier_map(array_group)

        for sel_obj in selection:
            mod = sel_obj.modifiers.new("Array", 'NODES')
            if not mod:
                continue
            mod.node_group = array_group

            def set_input(name, value):
                _set_gn_input(mod, ids.get(name), value)

            # GN Array counts the original as 1, so add 1
            set_input("Count", count + 1)

            if is_circle:
                rot_axis = _compute_circle_axis(
                    self.axis_x, self.axis_y, self.axis_z,
                    self.orientation, local_rot, context,
                )
                radius = diff.length

                # Always orient: local Z = rotation axis, Central Axis = Z.
                z = rot_axis.normalized()
                face_dir = _resolve_face_direction(
                    self.face_axis, self.orientation, local_rot, rot_axis,
                )
                if face_dir is not None:
                    y = face_dir
                    sel_obj.location = sel_obj.matrix_world.translation + diff / 2
                    radius = diff.length / 2
                else:
                    # Move object to cursor (circle center)
                    sel_obj.location = sel_obj.matrix_world.translation + diff
                    y = (-diff).normalized() if diff.length > 0 else z.orthogonal().normalized()
                    y = y - z * y.dot(z)
                    if y.length < 1e-6:
                        y = z.orthogonal()
                    y = y.normalized()
                x = y.cross(z)
                rot_matrix = Matrix((x, y, z)).transposed()
                sel_obj.rotation_euler = rot_matrix.to_euler()

                set_input("Shape", "Circle")
                set_input("Radius", radius)
                set_input("Central Axis", "Z")
                set_input("Circle Segment", "Full")
                set_input("Sweep Angle", 2 * pi)
                set_input("Offset", (0.0, 0.0, 0.0))
            else:
                local_step = sel_obj.matrix_world.inverted().to_3x3() @ step_offset
                set_input("Shape", "Line")
                set_input("Offset Method", "Offset")
                set_input("Translation", local_step[:])

            array_group.interface_update(context)

    def _create_duplicates(self, context):
        """Create duplicate objects using operator properties."""
        obj = bpy.data.objects.get(self.object_name) if self.object_name else context.active_object
        if not obj:
            return

        selection = list(context.selected_objects)
        if not selection:
            selection = [obj]

        origin = obj.matrix_world.translation.copy()
        local_rot = obj.matrix_world.to_3x3().normalized()
        point = Vector(self.location)
        count = self.count
        scale = self.dup_scale
        is_circle = self.mode == "CIRCLE"
        any_axis = self.axis_x or self.axis_y or self.axis_z
        sel_set = set(selection)

        new_objects = []
        copies = []
        if is_circle:
            diff = point - origin
            rot_axis = _compute_circle_axis(
                self.axis_x, self.axis_y, self.axis_z,
                self.orientation, local_rot, context,
            )

            face_dir = _resolve_face_direction(
                self.face_axis, self.orientation, local_rot, rot_axis,
            )

            for sel_obj in selection:
                org = sel_obj.matrix_world.translation
                if face_dir is not None:
                    start = face_dir * diff.length / 2
                    center = org + diff / 2
                else:
                    center = org + diff
                    start = -diff
                for i in range(1, count + 1):
                    angle = 2 * pi * i / (count + 1)
                    rot = Matrix.Rotation(angle, 3, rot_axis)
                    pos = center + rot @ start

                    new_obj = sel_obj.copy()
                    new_obj.data = sel_obj.data.copy()
                    is_child = sel_obj.parent and sel_obj.parent in sel_set
                    for col in sel_obj.users_collection:
                        col.objects.link(new_obj)
                    if not is_child:
                        new_obj.location = pos
                        new_obj.scale = sel_obj.scale * scale
                        if self.align:
                            self._apply_circle_align(new_obj, angle, rot_axis)
                    new_objects.append(new_obj)
                    copies.append((sel_obj, new_obj, i - 1))
        else:
            diff = point - origin
            factor = 2.0 if self.double else 1.0
            if not any_axis:
                offset = diff * factor
            else:
                r = local_rot if self.orientation == "LOCAL" else Matrix.Identity(3)
                offset = Vector((0, 0, 0))
                for name, enabled in [("x", self.axis_x), ("y", self.axis_y), ("z", self.axis_z)]:
                    if enabled:
                        d = r @ AXIS_DATA[name][0]
                        offset += d * factor * diff.dot(d)

            for sel_obj in selection:
                org = sel_obj.matrix_world.translation
                for i in range(1, count + 1):
                    t = i / count
                    s = 1.0 + (scale - 1.0) * t
                    pos = org + offset * t

                    new_obj = sel_obj.copy()
                    new_obj.data = sel_obj.data.copy()
                    is_child = sel_obj.parent and sel_obj.parent in sel_set
                    for col in sel_obj.users_collection:
                        col.objects.link(new_obj)
                    if not is_child:
                        new_obj.location = pos
                        new_obj.scale = sel_obj.scale * s
                    new_objects.append(new_obj)
                    copies.append((sel_obj, new_obj, i - 1))

        _remap_references(copies, selection, context)

        for sel_obj in selection:
            sel_obj.select_set(False)
        for new_obj in new_objects:
            new_obj.select_set(True)
        if new_objects:
            context.view_layer.objects.active = new_objects[0]

    def _cancel(self, context):
        context.area.header_text_set(text=None)
        infobar.remove(context)
        self._guide.remove()
        self._ghost.remove()
        context.area.tag_redraw()


classes = (ROTOR_OT_ArrayModal,)
