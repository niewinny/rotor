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
               orientation=None, double=False):
        has_axis = axis_x or axis_y or axis_z
        guide_color = self.COLOR_GRAY if has_axis else self.COLOR_BLACK

        org = Vector(origin)
        ep = Vector(endpoint)
        rot = orientation or Matrix.Identity(3)
        factor = 2.0 if double else 1.0

        guide_ep = ep if has_axis else org + (ep - org) * factor
        vertices = [origin[:], guide_ep[:]]
        colors = [guide_color, guide_color]
        indices = [(0, 1)]
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
            b = org + d * factor * diff.dot(d)
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


_BBOX_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)


class GhostDraw(DrawBase):
    """Draws a bounding-box wireframe ghost of an object at one or more positions."""

    COLOR_GHOST = (0.5, 0.5, 0.5, 0.5)

    def __init__(self):
        self.shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        self.batch = None
        self._edges = []

    def is_valid(self):
        return self.batch is not None

    def create_batch(self):
        return self.batch

    def set_object(self, obj):
        """Cache bounding-box edges as relative vectors (world transform applied, centered at origin)."""
        mat = obj.matrix_world
        origin = mat.translation
        bbox = [mat @ Vector(co) - origin for co in obj.bound_box]
        self._edges = [(bbox[a], bbox[b]) for a, b in _BBOX_EDGES]

    def update(self, placements):
        """Rebuild batch with cached edges offset and scaled per placement.

        placements: list of (position, scale) tuples.
        """
        if not self._edges or not placements:
            self.batch = None
            return
        vertices = []
        for pos, scale in placements:
            for v0_rel, v1_rel in self._edges:
                vertices.append((v0_rel * scale + pos)[:])
                vertices.append((v1_rel * scale + pos)[:])
        self.batch = batch_for_shader(
            self.shader, "LINES", {"pos": vertices},
        )

    def setup_draw_state(self, context):
        gpu.state.depth_test_set("NONE")
        self.shader.bind()
        self.shader.uniform_float("color", self.COLOR_GHOST)
        gpu.state.blend_set("ALPHA")
