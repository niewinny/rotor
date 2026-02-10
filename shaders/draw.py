import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector


AXIS_CROSS_LENGTH = 0.15

AXIS_DATA = {
    "x": (Vector((1, 0, 0)), (1.0, 0.2, 0.322, 1.0)),
    "y": (Vector((0, 1, 0)), (0.545, 0.863, 0.0, 1.0)),
    "z": (Vector((0, 0, 1)), (0.157, 0.564, 1.0, 1.0)),
}


class DrawBase:
    """Base class for GPU drawing with common functionality."""

    shader = None
    batch = None

    def create_batch(self):
        raise NotImplementedError

    def is_valid(self):
        return True

    def get_viewport_size(self, context):
        width = context.area.width
        height = context.area.height
        quad_view = getattr(context.space_data, "region_quadviews", None)
        if quad_view:
            width /= 2
            height /= 2
        return width, height

    def setup_draw_state(self, context):
        gpu.state.depth_test_set("NONE")
        self.shader.bind()
        gpu.state.blend_set("ALPHA")

    def draw(self, context):
        if not self.is_valid():
            return
        if self.batch is None:
            self.batch = self.create_batch()
        self.setup_draw_state(context)
        self.batch.draw(self.shader)


class GuideDraw(DrawBase):
    """Draws guide line + axis cross indicators at the endpoint."""

    COLOR_BLACK = (0.0, 0.0, 0.0, 1.0)
    COLOR_GRAY = (0.5, 0.5, 0.5, 1.0)

    def __init__(self):
        self.shader = gpu.shader.from_builtin("POLYLINE_FLAT_COLOR")
        self.batch = None
        self.width = 1.6

    def is_valid(self):
        return self.batch is not None

    def create_batch(self):
        return self.batch

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

        for name in ("x", "y", "z"):
            direction, color = AXIS_DATA[name]
            d = rot @ direction
            a = ep - d * AXIS_CROSS_LENGTH
            b = ep + d * AXIS_CROSS_LENGTH
            vertices.extend([a[:], b[:]])
            colors.extend([color, color])
            indices.append((idx, idx + 1))
            idx += 2

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

    def setup_draw_state(self, context):
        gpu.state.depth_test_set("NONE")
        self.shader.bind()
        vp_width, vp_height = self.get_viewport_size(context)
        self.shader.uniform_float("viewportSize", (vp_width, vp_height))
        self.shader.uniform_float("lineWidth", self.width)
        gpu.state.blend_set("ALPHA")
