import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from mathutils.geometry import intersect_line_plane
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

from ..utils import addon
from ..utils.scene import ray_cast


class GuideLine:
    """Draws a line between two 3D points in the viewport."""

    def __init__(self):
        self.shader = gpu.shader.from_builtin("POLYLINE_FLAT_COLOR")
        self.batch = None
        self.color = (0.0, 0.0, 0.0, 1.0)
        self.width = 1.6

    def update(self, point_a, point_b):
        vertices = [point_a[:], point_b[:]]
        vertex_colors = [self.color, self.color]
        self.batch = batch_for_shader(
            self.shader,
            "LINES",
            {"pos": vertices, "color": vertex_colors},
            indices=[(0, 1)],
        )

    def clear(self):
        self.batch = None

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
        ray_origin, ray_origin + ray_dir, origin, view_normal
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

        self.source_obj = obj
        self.exclude = {obj}
        self.origin = obj.matrix_world.translation.copy()
        self.guide = GuideLine()
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            self.guide.draw, (context,), "WINDOW", "POST_VIEW"
        )

        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == "MOUSEMOVE":
            snap_point = self._get_snap_point(context, event)
            if snap_point:
                self.guide.update(self.origin, snap_point)

        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._cleanup(context)
            return {"CANCELLED"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            self._cleanup(context)
            return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def _get_snap_point(self, context, event):
        region = context.region
        rv3d = context.region_data
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        snap = addon.pref().tools.duplicate.snap

        point = None
        match snap:
            case "ORIGIN":
                point = _snap_origin(context, mouse_pos, self.exclude)
            case "FACE":
                point = _snap_face(context, mouse_pos, self.exclude)
            case "VERTEX":
                point = _snap_vertex(context, mouse_pos, self.exclude)
            case "EDGE":
                point = _snap_edge(context, mouse_pos, self.exclude)
            case "EDGE_CENTER":
                point = _snap_edge_center(context, mouse_pos, self.exclude)
            case "FACE_CENTER":
                point = _snap_face_center(context, mouse_pos, self.exclude)

        # Fall back to view projection when no hit
        if point is None:
            point = _snap_view(self.origin, region, rv3d, mouse_pos)

        return point

    def _cleanup(self, context):
        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, "WINDOW")
            self._handle = None
        context.area.tag_redraw()


classes = (ROTOR_OT_DuplicateModal,)
