import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector
from mathutils.geometry import intersect_line_plane
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

from ..utils import addon
from ..utils.scene import ray_cast


AXIS_CROSS_LENGTH = 0.15

AXIS_DATA = {
    "x": (Vector((1, 0, 0)), (1.0, 0.2, 0.322, 1.0)),
    "y": (Vector((0, 1, 0)), (0.545, 0.863, 0.0, 1.0)),
    "z": (Vector((0, 0, 1)), (0.157, 0.564, 1.0, 1.0)),
}


class GuideDraw:
    """Draws guide line + axis cross indicators at the endpoint."""

    COLOR_BLACK = (0.0, 0.0, 0.0, 1.0)
    COLOR_GRAY = (0.5, 0.5, 0.5, 1.0)

    def __init__(self):
        self.shader = gpu.shader.from_builtin("POLYLINE_FLAT_COLOR")
        self.batch = None
        self.width = 1.6

    def update(self, origin, endpoint, axis_x=False, axis_y=False, axis_z=False,
               orientation=None):
        has_axis = axis_x or axis_y or axis_z
        guide_color = self.COLOR_GRAY if has_axis else self.COLOR_BLACK
        vertices = [origin[:], endpoint[:]]
        colors = [guide_color, guide_color]
        indices = [(0, 1)]

        org = Vector(origin)
        ep = Vector(endpoint)
        rot = orientation or Matrix.Identity(3)
        idx = 2

        # Small cross at endpoint — always all 3 axes
        for name in ("x", "y", "z"):
            direction, color = AXIS_DATA[name]
            d = rot @ direction
            a = ep - d * AXIS_CROSS_LENGTH
            b = ep + d * AXIS_CROSS_LENGTH
            vertices.extend([a[:], b[:]])
            colors.extend([color, color])
            indices.append((idx, idx + 1))
            idx += 2

        # Axis lines from origin — mirror across the guide endpoint per axis
        diff = ep - org
        axes = {"x": axis_x, "y": axis_y, "z": axis_z}
        for name, enabled in axes.items():
            if not enabled:
                continue
            direction, color = AXIS_DATA[name]
            d = rot @ direction
            b = org + d * 2.0 * diff.dot(d)
            vertices.extend([org[:], b[:]])
            colors.extend([color, color])
            indices.append((idx, idx + 1))
            idx += 2

        self.batch = batch_for_shader(
            self.shader,
            "LINES",
            {"pos": vertices, "color": colors},
            indices=indices,
        )

    def draw(self, context):
        if self.batch is None:
            return
        gpu.state.depth_test_set("NONE")
        self.shader.bind()
        vp_width = context.area.width
        vp_height = context.area.height
        quad_view = getattr(context.space_data, "region_quadviews", None)
        if quad_view:
            vp_width /= 2
            vp_height /= 2
        self.shader.uniform_float("viewportSize", (vp_width, vp_height))
        self.shader.uniform_float("lineWidth", self.width)
        gpu.state.blend_set("ALPHA")
        self.batch.draw(self.shader)


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
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            self.report({"WARNING"}, f"Object '{self.object_name}' not found")
            return {"CANCELLED"}

        self._exclude = {obj}
        self._selection = [o for o in context.selected_objects]
        self._origin = obj.matrix_world.translation.copy()
        self._local_rot = obj.matrix_world.to_3x3().normalized()
        self._guide = GuideDraw()
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            self._guide.draw, (context,), "WINDOW", "POST_VIEW"
        )
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

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

        if event.type == "MOUSEMOVE":
            point = self._snap(context, event)
            if point:
                rot = self._local_rot if dup.snap.orientation == "LOCAL" else None
                self._guide.update(
                    self._origin, point,
                    axis_x=dup.axis_x, axis_y=dup.axis_y, axis_z=dup.axis_z,
                    orientation=rot,
                )

        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._cleanup(context)
            return {"CANCELLED"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            self._cleanup(context)
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

    def _cleanup(self, context):
        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, "WINDOW")
            self._handle = None
        context.area.tag_redraw()


classes = (ROTOR_OT_DuplicateModal,)
