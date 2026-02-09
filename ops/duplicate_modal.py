import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from mathutils.geometry import intersect_line_plane
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d


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
            region = context.region
            rv3d = context.region_data
            mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

            ray_origin = region_2d_to_origin_3d(region, rv3d, mouse_pos)
            ray_dir = region_2d_to_vector_3d(region, rv3d, mouse_pos)

            # Project onto plane at origin facing the view
            if rv3d.is_perspective:
                view_normal = (ray_origin - self.origin).normalized()
            else:
                view_normal = -rv3d.view_matrix.inverted().col[2].to_3d().normalized()

            point_on_plane = intersect_line_plane(
                ray_origin, ray_origin + ray_dir, self.origin, view_normal
            )

            if point_on_plane:
                self.guide.update(self.origin, point_on_plane)

        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._cleanup(context)
            return {"CANCELLED"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            self._cleanup(context)
            return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def _cleanup(self, context):
        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, "WINDOW")
            self._handle = None
        context.area.tag_redraw()


classes = (ROTOR_OT_DuplicateModal,)
