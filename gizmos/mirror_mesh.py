import bpy
from mathutils import Matrix, Vector

from ..ops.mirror_mesh_utils import get_mesh_mirror_frame
from ..utils import addon
from .mirror import (
    ARROW_AXES,
    create_mirror_gizmo,
    lighter,
    set_mirror_gizmo,
)

# Orientation of the arrow_3d gizmo (default points +Z) onto each signed axis.
AXIS_MATRICES = {
    "X+": Matrix(([0, 0, 1], [0, 1, 0], [-1, 0, 0])),
    "X-": Matrix(([0, 0, -1], [0, 1, 0], [1, 0, 0])),
    "Y+": Matrix(([1, 0, 0], [0, 0, 1], [0, -1, 0])),
    "Y-": Matrix(([1, 0, 0], [0, 0, -1], [0, 1, 0])),
    "Z+": Matrix(([1, 0, 0], [0, 1, 0], [0, 0, 1])),
    "Z-": Matrix(([-1, 0, 0], [0, 1, 0], [0, 0, -1])),
}

FADE_THRESHOLD = 0.985


class ROTOR_GGT_MirrorMeshGizmoGroup(bpy.types.GizmoGroup):
    """Axis gizmos for the edit-mode Mirror tool.

    Arrows (handles) mirror the selection; boxes (dots) mirror the full mesh.
    Both are placed on the mirror plane derived from the current selection.
    """

    bl_idname = "ROTOR_GGT_MirrorMeshGizmoGroup"
    bl_label = "Mirror Mesh Gizmo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D", "SHOW_MODAL_ALL"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gizmos_arrows = []
        self.gizmos_boxes = []

    @classmethod
    def poll(cls, context):
        active_tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        )
        return bool(
            active_tool
            and active_tool.idname == "mirror.mirror_mesh_tool"
            and context.mode == "EDIT_MESH"
            and context.edit_object
            and context.edit_object.type == "MESH"
        )

    def setup(self, context):
        self.gizmos_arrows.clear()
        self.gizmos_boxes.clear()

        theme_axis = addon.pref().theme.axis
        pref = addon.pref().tools.mesh
        gizmo_size = addon.pref().tools.gizmo_size
        reverse = pref.reverse_controls

        for idx, (_axis_vec, axis_name, tag) in enumerate(ARROW_AXES):
            axis = tag[0]
            original_sign = "POS" if tag[1] == "+" else "NEG"
            sign = ("NEG" if original_sign == "POS" else "POS") if reverse else original_sign

            # Handle (arrow) -> mirror selection
            handle_color = theme_axis.g
            highlight = getattr(theme_axis, axis_name)
            gz_arrow = create_mirror_gizmo(self, axis, handle_color, idx, gizmo_size)
            gz_arrow.color_highlight = lighter(highlight, 0.5)[:3]
            gz_arrow.alpha_highlight = highlight[3]
            op = gz_arrow.target_set_operator("mirror.mirror_mesh")
            op.axis = axis
            op.sign = sign
            op.target = "SELECTION"
            self.gizmos_arrows.append((gz_arrow, tag))

            # Dot (box) -> mirror full mesh
            box_color = getattr(theme_axis, axis_name)
            gz_box = set_mirror_gizmo(self, axis, box_color, idx, gizmo_size)
            gz_box.color_highlight = lighter(box_color, 0.5)[:3]
            gz_box.alpha_highlight = box_color[3]
            op = gz_box.target_set_operator("mirror.mirror_mesh")
            op.axis = axis
            op.sign = sign
            op.target = "MESH"
            self.gizmos_boxes.append((gz_box, tag))

    @staticmethod
    def _axis_vector(tag):
        axis, sign = tag[0].lower(), 1 if tag[1] == "+" else -1
        if axis == "x":
            return Vector((sign, 0, 0))
        if axis == "y":
            return Vector((0, sign, 0))
        return Vector((0, 0, sign))

    def _camera_info(self, context, origin):
        rv3d = context.region_data
        if rv3d:
            inv = rv3d.view_matrix.inverted()
            view_dir = -inv.col[2].to_3d().normalized()
            if rv3d.is_perspective:
                return inv.translation, view_dir, True
            return Vector((0, 0, 0)), view_dir, False
        return Vector((0, 0, 0)), Vector((0, 0, -1)), True

    @staticmethod
    def _alpha_mult(dot):
        a = abs(dot)
        if a > FADE_THRESHOLD:
            return 1.0 - ((a - FADE_THRESHOLD) / (1.0 - FADE_THRESHOLD))
        return 1.0

    def draw_prepare(self, context):
        all_gizmos = self.gizmos_arrows + self.gizmos_boxes

        frame_data = get_mesh_mirror_frame(context)
        if frame_data is None:
            for gz, _ in all_gizmos:
                gz.hide = True
            return

        origin, frame = frame_data
        rot4 = frame.to_4x4()
        theme_axis = addon.pref().theme.axis
        camera_pos, view_direction, use_perspective = self._camera_info(context, origin)

        def alpha_for(tag):
            axis_world = (frame @ self._axis_vector(tag)).normalized()
            if use_perspective:
                dot = (camera_pos - origin).normalized().dot(axis_world)
            else:
                dot = -view_direction.dot(axis_world)
            return self._alpha_mult(dot)

        for gz, tag in self.gizmos_arrows:
            gz.hide = False
            m = rot4 @ AXIS_MATRICES[tag].to_4x4()
            m.translation = origin
            gz.matrix_basis = m
            color = theme_axis.g
            gz.color = color[:3]
            gz.alpha = color[3] * alpha_for(tag)

        for idx, (gz, tag) in enumerate(self.gizmos_boxes):
            gz.hide = False
            m = rot4 @ AXIS_MATRICES[tag].to_4x4()
            m.translation = origin
            gz.matrix_basis = m
            color = getattr(theme_axis, ARROW_AXES[idx][1])
            gz.color = color[:3]
            gz.alpha = color[3] * alpha_for(tag)


classes = (ROTOR_GGT_MirrorMeshGizmoGroup,)
