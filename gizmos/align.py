import bpy
from mathutils import Vector, Matrix
from bpy_extras.view3d_utils import location_3d_to_region_2d

from ..utils import addon

# (axis vector, axis name, tag)
ARROW_AXES = [
    (Vector((1, 0, 0)), "x", "X+"),
    (Vector((-1, 0, 0)), "x", "X-"),
    (Vector((0, 1, 0)), "y", "Y+"),
    (Vector((0, -1, 0)), "y", "Y-"),
    (Vector((0, 0, 1)), "z", "Z+"),
    (Vector((0, 0, -1)), "z", "Z-"),
]

# Each arrow's local +Z is oriented to point INWARD (toward the target).
INWARD_MATRICES = {
    "X+": Matrix(([0, 0, -1], [0, 1, 0], [1, 0, 0])),   # local +Z = -X
    "X-": Matrix(([0, 0, 1], [0, 1, 0], [-1, 0, 0])),   # local +Z = +X
    "Y+": Matrix(([1, 0, 0], [0, 0, -1], [0, 1, 0])),   # local +Z = -Y
    "Y-": Matrix(([1, 0, 0], [0, 0, 1], [0, -1, 0])),   # local +Z = +Y
    "Z+": Matrix(([-1, 0, 0], [0, 1, 0], [0, 0, -1])),  # local +Z = -Z
    "Z-": Matrix(([1, 0, 0], [0, 1, 0], [0, 0, 1])),    # local +Z = +Z
}

# Match the mirror gizmo's arrow values so the two tools render at the same
# apparent size at any view zoom.
ARROW_LENGTH = 1.1
ARROW_SCALE_BASIS = 1.4
# Extra outward offset between the cone tip and the target, in the same
# scaled units as the arrow itself (so the gap stays proportional at any zoom).
ARROW_GAP = 0.4


def lighter(color, amt=0.5):
    return tuple(
        min(1.0, v + (1.0 - v) * amt) if i < 3 else color[3]
        for i, v in enumerate(color)
    )


def _axis_vector(axis: str, sign: int) -> Vector:
    if axis == "x":
        return Vector((sign, 0, 0))
    if axis == "y":
        return Vector((0, sign, 0))
    return Vector((0, 0, sign))


def _bbox_face_center(obj, outward_world: Vector) -> Vector:
    """World-space center of the bbox face whose outward normal best aligns
    with outward_world. The direction of outward_world fully picks the side
    (+X vs -X, +Y vs -Y, etc.) so no separate sign argument is needed."""
    mat = obj.matrix_world
    corners = [mat @ Vector(c) for c in obj.bound_box]
    bbox_center = Vector((0.0, 0.0, 0.0))
    for c in corners:
        bbox_center = bbox_center + c
    bbox_center = bbox_center / len(corners)
    max_extent = max((c - bbox_center).dot(outward_world) for c in corners)
    return bbox_center + outward_world * max_extent


def _gizmo_world_scale(context, world_pos: Vector, size: float) -> float:
    """World-space scale factor matching Blender's screen-scaled gizmos.

    Blender computes ``scale_final = pixel_size_at_depth * U.gizmo_size *
    scale_basis`` for 3D gizmos. We replicate it here so our world-scaled
    align arrows render at the same apparent size as the mirror tool's
    screen-scaled arrows at every zoom level."""
    region = context.region
    rv3d = context.region_data
    fallback = ARROW_SCALE_BASIS * size
    if not rv3d or not region:
        return fallback
    view_right = rv3d.view_matrix.inverted().col[0].to_3d().normalized()
    p0 = location_3d_to_region_2d(region, rv3d, world_pos)
    p1 = location_3d_to_region_2d(region, rv3d, world_pos + view_right)
    if p0 is None or p1 is None:
        return fallback
    pixel_dist = (p1 - p0).length
    if pixel_dist < 1e-6:
        return fallback
    world_per_pixel = 1.0 / pixel_dist
    gizmo_size_px = context.preferences.view.gizmo_size
    return ARROW_SCALE_BASIS * size * gizmo_size_px * world_per_pixel


def _create_align_arrow(group, color):
    gz = group.gizmos.new("GIZMO_GT_arrow_3d")
    gz.color = color[:3]
    gz.alpha = color[3]
    gz.color_highlight = lighter(color, 0.5)[:3]
    gz.alpha_highlight = color[3]
    gz.use_draw_modal = False
    gz.hide_select = False
    gz.length = ARROW_LENGTH
    # We manually replicate Blender's per-view scaling each frame, so the
    # built-in screen-scaling is off.
    gz.use_draw_scale = False
    gz.matrix_basis = Matrix.Identity(4)
    gz.matrix_offset = Matrix.Identity(4)
    gz.draw_style = "NORMAL"
    return gz


class ROTOR_GGT_AlignGizmoGroup(bpy.types.GizmoGroup):
    """GizmoGroup for the Align tool. Shows two sets of axis arrows: one
    around the world origin and one around the active object. Each arrow's
    cone tip points at the target it will align objects to."""

    bl_idname = "ROTOR_GGT_AlignGizmoGroup"
    bl_label = "Align Gizmo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D", "SHOW_MODAL_ALL"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gizmos_world = []
        self.gizmos_active = []
        self.gizmos_cursor = []

    @classmethod
    def poll(cls, context) -> bool:
        active_tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        )
        if not (active_tool and active_tool.idname == "mirror.align_tool"):
            return False
        selected = [obj for obj in context.selected_objects if obj.type == "MESH"]
        return bool(selected)

    def setup(self, context):
        self.gizmos_world.clear()
        self.gizmos_active.clear()
        self.gizmos_cursor.clear()

        theme_axis = addon.pref().theme.axis

        for _, axis_name, tag in ARROW_AXES:
            color = getattr(theme_axis, axis_name)

            gz_w = _create_align_arrow(self, color)
            op = gz_w.target_set_operator("mirror.align_axis")
            op.target = "WORLD"
            op.axis = tag[0]
            op.sign = "POS" if tag[1] == "+" else "NEG"
            self.gizmos_world.append((gz_w, tag))

            gz_a = _create_align_arrow(self, color)
            op = gz_a.target_set_operator("mirror.align_axis")
            op.target = "ACTIVE"
            op.axis = tag[0]
            op.sign = "POS" if tag[1] == "+" else "NEG"
            self.gizmos_active.append((gz_a, tag))

            gz_c = _create_align_arrow(self, color)
            op = gz_c.target_set_operator("mirror.align_axis")
            op.target = "CURSOR"
            op.axis = tag[0]
            op.sign = "POS" if tag[1] == "+" else "NEG"
            self.gizmos_cursor.append((gz_c, tag))

    def draw_prepare(self, context):
        pref = addon.pref()
        theme_axis = pref.theme.axis
        align_tool = pref.tools.align
        orientation = align_tool.orientation
        size = pref.tools.gizmo_size

        active = context.active_object
        has_active = active is not None and active.select_get()

        rv3d = context.region_data
        if rv3d:
            view_matrix_inv = rv3d.view_matrix.inverted()
            view_direction = -view_matrix_inv.col[2].to_3d().normalized()
            use_perspective = rv3d.is_perspective
            camera_pos = view_matrix_inv.translation if use_perspective else Vector((0, 0, 0))
        else:
            camera_pos = Vector((0, 0, 0))
            view_direction = Vector((0, 0, -1))
            use_perspective = True

        world_origin = Vector((0, 0, 0))
        active_origin = active.matrix_world.translation.copy() if has_active else None

        show_world = align_tool.target_world
        show_active = align_tool.target_active and has_active
        show_cursor = align_tool.target_cursor
        use_bbox_target = align_tool.target_source == "BBOX"

        # Scale at world origin (single value — world set always shares one target).
        scale_world = _gizmo_world_scale(context, world_origin, size) if show_world else 0.0

        # World gizmos: global axes; tips point toward the world origin.
        for gz, tag in self.gizmos_world:
            if not show_world:
                gz.hide = True
                continue
            gz.hide = False
            axis_name = tag[0].lower()
            sign = 1 if tag[1] == "+" else -1
            outward_world = _axis_vector(axis_name, sign)
            alpha_mult = self._alpha_for(camera_pos, world_origin, outward_world, view_direction, use_perspective)
            scale_m = Matrix.Diagonal((scale_world, scale_world, scale_world, 1.0))
            m = INWARD_MATRICES[tag].to_4x4() @ scale_m
            m.translation = world_origin + outward_world * (ARROW_LENGTH + ARROW_GAP) * scale_world
            gz.matrix_basis = m
            color = getattr(theme_axis, axis_name)
            gz.color = color[:3]
            gz.alpha = color[3] * alpha_mult
            gz.color_highlight = lighter(color, 0.5)[:3]
            gz.alpha_highlight = color[3]

        # Active gizmos: rotate outward direction by active's matrix in LOCAL mode.
        active_rot4 = (
            active.matrix_world.to_3x3().normalized().to_4x4()
            if (has_active and orientation == "LOCAL")
            else Matrix.Identity(4)
        )
        active_rot3 = active_rot4.to_3x3()

        # Cursor gizmos: positioned at the 3D cursor, oriented by the cursor's
        # rotation in LOCAL mode, world axes in GLOBAL mode.
        cursor = context.scene.cursor
        cursor_pos = cursor.location.copy()
        cursor_rot4 = (
            cursor.matrix.to_3x3().to_4x4()
            if orientation == "LOCAL"
            else Matrix.Identity(4)
        )
        cursor_rot3 = cursor_rot4.to_3x3()
        for gz, tag in self.gizmos_cursor:
            if not show_cursor:
                gz.hide = True
                continue
            gz.hide = False
            axis_name = tag[0].lower()
            sign = 1 if tag[1] == "+" else -1
            outward_local = _axis_vector(axis_name, sign)
            outward_world = (cursor_rot3 @ outward_local).normalized()
            scale = _gizmo_world_scale(context, cursor_pos, size)
            alpha_mult = self._alpha_for(camera_pos, cursor_pos, outward_world, view_direction, use_perspective)
            scale_m = Matrix.Diagonal((scale, scale, scale, 1.0))
            m = cursor_rot4 @ INWARD_MATRICES[tag].to_4x4() @ scale_m
            m.translation = cursor_pos + outward_world * (ARROW_LENGTH + ARROW_GAP) * scale
            gz.matrix_basis = m
            color = getattr(theme_axis, axis_name)
            gz.color = color[:3]
            gz.alpha = color[3] * alpha_mult
            gz.color_highlight = lighter(color, 0.5)[:3]
            gz.alpha_highlight = color[3]

        for gz, tag in self.gizmos_active:
            if not show_active:
                gz.hide = True
                continue
            gz.hide = False
            axis_name = tag[0].lower()
            sign = 1 if tag[1] == "+" else -1
            outward_local = _axis_vector(axis_name, sign)
            outward_world = (active_rot3 @ outward_local).normalized()
            # In BBox-target mode each arrow points at its own bbox-face
            # center; in Origin mode they all converge on the active object.
            target_point = (
                _bbox_face_center(active, outward_world)
                if use_bbox_target else active_origin
            )
            scale = _gizmo_world_scale(context, target_point, size)
            alpha_mult = self._alpha_for(camera_pos, target_point, outward_world, view_direction, use_perspective)
            scale_m = Matrix.Diagonal((scale, scale, scale, 1.0))
            m = active_rot4 @ INWARD_MATRICES[tag].to_4x4() @ scale_m
            m.translation = target_point + outward_world * (ARROW_LENGTH + ARROW_GAP) * scale
            gz.matrix_basis = m
            color = getattr(theme_axis, axis_name)
            gz.color = color[:3]
            gz.alpha = color[3] * alpha_mult
            gz.color_highlight = lighter(color, 0.5)[:3]
            gz.alpha_highlight = color[3]

    @staticmethod
    def _alpha_for(camera_pos, origin, axis_world, view_direction, use_perspective):
        if origin is None:
            return 1.0
        if use_perspective:
            to_camera = (camera_pos - origin).normalized()
            dot = to_camera.dot(axis_world)
        else:
            dot = -view_direction.dot(axis_world)
        fade_threshold = 0.985
        abs_dot = abs(dot)
        if abs_dot > fade_threshold:
            return 1.0 - ((abs_dot - fade_threshold) / (1.0 - fade_threshold))
        return 1.0


classes = (ROTOR_GGT_AlignGizmoGroup,)
