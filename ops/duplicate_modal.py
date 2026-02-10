import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import intersect_line_plane
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

from ..utils import addon
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

_PIVOT_CYCLE = ("VIEW", "ORIGIN", "FACE", "VERTEX", "EDGE", "EDGE_CENTER", "FACE_CENTER")
_ORIENTATION_CYCLE = ("GLOBAL", "LOCAL")


class ROTOR_OT_DuplicateModal(bpy.types.Operator):
    """Duplicate object with visual guide"""

    bl_idname = "rotor.duplicate_modal"
    bl_label = "Rotor Duplicate"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    object_name: bpy.props.StringProperty(
        name="Object",
        description="Name of the object to duplicate",
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
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    @safe
    def modal(self, context, event):
        context.area.tag_redraw()
        dup = addon.pref().tools.duplicate

        if event.type in {"X", "Y", "Z"} and event.value == "PRESS":
            attr = f"axis_{event.type.lower()}"
            setattr(dup, attr, not getattr(dup, attr))
            return {"RUNNING_MODAL"}

        if event.type == "O" and event.value == "PRESS":
            cur = _ORIENTATION_CYCLE.index(dup.snap.orientation)
            dup.snap.orientation = _ORIENTATION_CYCLE[(cur + 1) % len(_ORIENTATION_CYCLE)]
            return {"RUNNING_MODAL"}

        if event.type == "P" and event.value == "PRESS":
            cur = _PIVOT_CYCLE.index(dup.snap.pivot)
            dup.snap.pivot = _PIVOT_CYCLE[(cur + 1) % len(_PIVOT_CYCLE)]
            return {"RUNNING_MODAL"}

        if event.type == "RIGHT_BRACKET" and event.value == "PRESS":
            dup.count += 1
            return {"RUNNING_MODAL"}

        if event.type == "LEFT_BRACKET" and event.value == "PRESS":
            if dup.count > 1:
                dup.count -= 1
            return {"RUNNING_MODAL"}

        if event.type == "QUOTE" and event.value == "PRESS":
            step = 0.01 if event.shift else 0.1
            dup.scale = round(dup.scale + step, 2)
            return {"RUNNING_MODAL"}

        if event.type == "SEMI_COLON" and event.value == "PRESS":
            step = 0.01 if event.shift else 0.1
            dup.scale = max(0.01, round(dup.scale - step, 2))
            return {"RUNNING_MODAL"}

        if event.type == "MOUSEMOVE":
            point = self._snap(context, event)
            if point:
                self._last_point = point
                rot = self._local_rot if dup.snap.orientation == "LOCAL" else None
                self._guide.callback.update(
                    self._origin, point,
                    axis_x=dup.axis_x, axis_y=dup.axis_y, axis_z=dup.axis_z,
                    orientation=rot,
                )
                self._ghost.callback.update(
                    self._ghost_positions(point, dup)
                )

        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._cancel(context)
            return {"CANCELLED"}

        if ((event.type == "LEFTMOUSE" and event.value == "RELEASE")
                or (event.type in {"SPACE", "RET"} and event.value == "PRESS")):
            self._finish(context)
            return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def _snap(self, context, event):
        region = context.region
        rv3d = context.region_data
        mouse = Vector((event.mouse_region_x, event.mouse_region_y))

        snap_fn = _SNAP_FUNCTIONS.get(addon.pref().tools.duplicate.snap.pivot)
        point = snap_fn(context, mouse, self._exclude) if snap_fn else None

        # Raycast may deselect objects — restore selection
        for obj in self._selection:
            if not obj.select_get():
                obj.select_set(True)

        if point is None:
            point = _snap_view(self._origin, region, rv3d, mouse)
        return point

    def _ghost_offsets(self, point, dup):
        """Compute direction offsets from grabbed object's origin."""
        diff = point - self._origin
        any_axis = dup.axis_x or dup.axis_y or dup.axis_z
        offsets = []
        if not any_axis:
            offsets.append(diff)
        else:
            r = self._local_rot if dup.snap.orientation == "LOCAL" else Matrix.Identity(3)
            for name, enabled in [("x", dup.axis_x), ("y", dup.axis_y), ("z", dup.axis_z)]:
                if not enabled:
                    continue
                d = r @ AXIS_DATA[name][0]
                offsets.append(d * 2.0 * diff.dot(d))
        return offsets

    def _ghost_positions(self, point, dup):
        """Compute ghost placements (position, scale) subdivided by count."""
        count = dup.count
        scale = dup.scale
        offsets = self._ghost_offsets(point, dup)
        placements = []
        for org in self._origins:
            for offset in offsets:
                for i in range(1, count + 1):
                    t = i / count
                    s = 1.0 + (scale - 1.0) * t
                    placements.append((org + offset * t, s))
        return placements

    def _finish(self, context):
        """Create real duplicates at ghost positions, then clean up."""
        self._guide.remove()
        self._ghost.remove()
        if not self._last_point:
            context.area.tag_redraw()
            return

        dup = addon.pref().tools.duplicate
        count = dup.count
        scale = dup.scale
        offsets = self._ghost_offsets(self._last_point, dup)

        new_objects = []
        for obj in self._selection:
            org = obj.matrix_world.translation
            for offset in offsets:
                for i in range(1, count + 1):
                    t = i / count
                    s = 1.0 + (scale - 1.0) * t
                    pos = org + offset * t

                    new_obj = obj.copy()
                    new_obj.data = obj.data.copy()
                    for col in obj.users_collection:
                        col.objects.link(new_obj)
                    new_obj.location = pos
                    new_obj.scale = obj.scale * s
                    new_objects.append(new_obj)

        # Select only the new objects
        for obj in self._selection:
            obj.select_set(False)
        for obj in new_objects:
            obj.select_set(True)
        if new_objects:
            context.view_layer.objects.active = new_objects[0]

        context.area.tag_redraw()

    def _cancel(self, context):
        self._guide.remove()
        self._ghost.remove()
        context.area.tag_redraw()


classes = (ROTOR_OT_DuplicateModal,)
