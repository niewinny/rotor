import bpy
from mathutils import Vector, Matrix
from ..utils import addon

# Helper: axis info for 
alpha = 0.8
ARROW_AXES = [
    (Vector((1, 0, 0)), 'x', 'X+'),   # Red +X
    (Vector((-1, 0, 0)), 'x', 'X-'),  # Red -X
    (Vector((0, 1, 0)), 'y', 'Y+'),   # Green +Y
    (Vector((0, -1, 0)), 'y', 'Y-'),  # Green -Y
    (Vector((0, 0, 1)), 'z', 'Z+'),   # Blue +Z
    (Vector((0, 0, -1)), 'z', 'Z-'),  # Blue -Z
]


def lighter(color, amt=0.5):
    # color: (r,g,b,a), amt: 0..1, returns lighter color
    return tuple(
        min(1.0, v + (1.0 - v) * amt) if i < 3 else color[3]
        for i, v in enumerate(color)
    )


def create_collection_gizmo(group, axis, color, idx):
    gz = group.gizmos.new("GIZMO_GT_arrow_3d")
    gz.color = color[:3]
    gz.alpha = color[3]
    gz.color_highlight = lighter(color, 0.5)[:3]
    gz.alpha_highlight = color[3]
    gz.scale_basis = 1.2
    gz.use_draw_modal = False
    gz.hide_select = False
    gz.length = 1.1
    gz.matrix_basis = Matrix.Identity(4)
    gz.draw_style = 'BOX'
    return gz


def create_mirror_gizmo(group, axis, color, idx):
    gz = group.gizmos.new("GIZMO_GT_arrow_3d")
    gz.color = color[:3]
    gz.alpha = color[3]
    gz.color_highlight = lighter(color, 0.5)[:3]
    gz.alpha_highlight = color[3]
    gz.scale_basis = 1.2
    gz.use_draw_modal = False
    gz.hide_select = False
    gz.length = 1.1
    gz.matrix_basis = Matrix.Identity(4)
    gz.draw_style = 'BOX'
    return gz


def set_mirror_gizmo(group, axis, color, idx):
    gz = group.gizmos.new("GIZMO_GT_arrow_3d")
    gz.color = color[:3]
    gz.alpha = color[3]
    gz.color_highlight = lighter(color, 0.5)[:3]
    gz.alpha_highlight = color[3]
    gz.scale_basis = 0.7
    gz.use_draw_modal = False
    gz.hide_select = False
    gz.length = 2.8
    gz.matrix_basis = Matrix.Identity(4)
    gz.draw_options = set()
    gz.draw_style = 'BOX'
    return gz



class ROTOR_GGT_MirrorGizmoGroup(bpy.types.GizmoGroup):
    """
    GizmoGroup for Rotor Mirror Tool. Displays axis arrow gizmos for mirroring operations in the 3D view.
    """
    bl_idname = "ROTOR_GGT_MirrorGizmoGroup"
    bl_label = "Rotor Mirror Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'SHOW_MODAL_ALL'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_highlighted_tag = None
        self.gizmos_arrows = []
        self.gizmos_boxes = []
        self.gizmos_colelction_arrows = []


    @classmethod
    def poll(cls, context) -> bool:
        """Show gizmos only when the rotor mirror tool is active and objects are selected."""
        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        return bool(active_tool and active_tool.idname == 'rotor.mirror_tool' and selected_objects)

    def _get_arrow_colors_and_highlights(self, context):
        """Return (arrow_colors, arrow_highlights) for the 6 gizmo arrows based on the last mirror modifier."""
        theme_axis = addon.pref().theme.axis
        axis_color_names = ['x', 'x', 'y', 'y', 'z', 'z']
        axis_highlight_names = ['x', 'x', 'y', 'y', 'z', 'z']
        # Default: all axis colors
        arrow_colors = [theme_axis.g] * 6
        arrow_highlights = [getattr(theme_axis, axis_highlight_names[i]) for i in range(6)]

        # Find active mesh
        active_mesh = context.active_object if (context.active_object and context.active_object.type == 'MESH' and context.active_object.select_get()) else None
        if not active_mesh:
            selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
            active_mesh = selected_meshes[0] if selected_meshes else None

        if active_mesh:
            # Find last mirror modifier
            mirror_mod = None
            for mod in reversed(active_mesh.modifiers):
                if mod.type == 'MIRROR':
                    mirror_mod = mod
                    break
            if mirror_mod:
              # Start with all gray, only color used axes  
                for i, (pos_idx, neg_idx) in enumerate([(0,1), (2,3), (4,5)]):
                    axis_color = getattr(theme_axis, 'xyz'[i])
                    if mirror_mod.use_axis[i]:
                        if mirror_mod.use_bisect_flip_axis[i]:
                            # Negative axis (X-, Y-, Z-)
                            arrow_colors[neg_idx] = axis_color
                        else:
                            # Positive axis (X+, Y+, Z+)
                            arrow_colors[pos_idx] = axis_color
                # Highlights always axis color
                arrow_highlights = [getattr(theme_axis, axis_color_names[i]) for i in range(6)]
        return arrow_colors, arrow_highlights

    def setup(self, context):
        """Create axis arrow gizmos with color logic based on mirror modifier, and box gizmos with always axis color."""
        self.gizmos_arrows.clear()
        self.gizmos_boxes.clear()
        self.gizmos_colelction_arrows.clear()

        arrow_colors, arrow_highlights = self._get_arrow_colors_and_highlights(context)

        theme_axis = addon.pref().theme.axis
        element = addon.pref().tools.mirror.element
        hide_collection_gizmos = True if element == 'OBJECT' else False
        hide_mirror_gizmos = True if element == 'COLLECTION' else False

        for idx, (axis, axis_name, tag) in enumerate(ARROW_AXES):
            axis = tag[0].upper()  # 'X', 'Y', 'Z'
            sign = 'POS' if tag[1] == '+' else 'NEG'
            color = arrow_colors[idx]
            axis_highlight_color = arrow_highlights[idx]

            gz_arrow = create_mirror_gizmo(self, axis, color, idx)
            gz_arrow.color_highlight = lighter(axis_highlight_color, 0.5)[:3]
            gz_arrow.alpha_highlight = axis_highlight_color[3]
            gz_op = gz_arrow.target_set_operator("rotor.set_mirror_axis")
            gz_op.axis = axis
            gz_op.sign = sign
            gz_arrow.hide = hide_mirror_gizmos
            self.gizmos_arrows.append((gz_arrow, tag))

            main_color = theme_axis.n
            gz_collection_arrow = create_collection_gizmo(self, axis, main_color, idx)
            gz_collection_arrow.color_highlight = lighter(color, 0.5)[:3]
            gz_collection_arrow.alpha_highlight = color[3]
            gz_op = gz_collection_arrow.target_set_operator("rotor.add_mirror_collection")
            gz_op.axis = axis
            gz_op.sign = sign
            gz_collection_arrow.hide = hide_collection_gizmos
            self.gizmos_colelction_arrows.append((gz_collection_arrow, tag))

            main_color = getattr(addon.pref().theme.axis, axis_name)
            gz_box = set_mirror_gizmo(self, axis, main_color, idx)
            gz_box.color_highlight = lighter(color, 0.5)[:3]
            gz_box.alpha_highlight = color[3]
            gz_op = gz_box.target_set_operator("rotor.add_mirror_axis")
            gz_op.axis = axis
            gz_op.sign = sign
            gz_box.hide_select = hide_mirror_gizmos
            self.gizmos_boxes.append((gz_box, tag))


    def draw_prepare(self, context):
        """Update gizmo transforms, colors, and highlights each frame."""
        pref = addon.pref()
        mirror_tool = pref.tools.mirror
        orientation = getattr(mirror_tool, 'orientation', 'GLOBAL')
        pivot = getattr(mirror_tool, 'pivot', 'ACTIVE')
        origin = self._get_origin(context, pivot)
        mat = self._get_orientation_matrix(context, orientation)
        camera_pos, view_direction, use_perspective = self._get_camera_info(context, origin)
        axis_matrices = self._get_axis_matrices()
        arrow_colors, arrow_highlights = self._get_arrow_colors_and_highlights(context)
        obj = context.active_object

        hide_collection_gizmos = True if mirror_tool.element == 'OBJECT' else False
        hide_mirror_gizmos = True if mirror_tool.element == 'COLLECTION' else False

        for idx, (gz_arrow, tag) in enumerate(self.gizmos_colelction_arrows):
            axis, sign = tag[0].lower(), 1 if tag[1] == '+' else -1
            axis_vec = self._axis_vector(axis, sign)
            axis_world = mat @ axis_vec if orientation in ('LOCAL', 'CURSOR') else axis_vec
            dot = self._get_dot(camera_pos, origin, axis_world, view_direction, use_perspective)
            alpha_mult = self._get_alpha_mult(dot)
            arrow_m = axis_matrices[tag].to_4x4()
            if orientation == 'LOCAL' and obj:
                rot_mat = obj.matrix_world.to_3x3().normalized().to_4x4()
                arrow_m = rot_mat @ arrow_m
            elif orientation == 'CURSOR':
                rot_mat = context.scene.cursor.rotation_euler.to_matrix().to_4x4()
                arrow_m = rot_mat @ arrow_m
            arrow_m.translation = origin
            gz_arrow.matrix_basis = arrow_m
            color = getattr(addon.pref().theme.axis, 'n')
            highlight_color = arrow_highlights[idx]
            gz_arrow.color = color[:3]
            gz_arrow.alpha = color[3] * alpha_mult
            gz_arrow.color_highlight = lighter(highlight_color, 0.5)[:3]
            gz_arrow.alpha_highlight = highlight_color[3]
            gz_arrow.hide = hide_collection_gizmos
            self._update_highlight(gz_arrow, tag)

        for idx, (gz_arrow, tag) in enumerate(self.gizmos_arrows):
            axis, sign = tag[0].lower(), 1 if tag[1] == '+' else -1
            axis_vec = self._axis_vector(axis, sign)
            axis_world = mat @ axis_vec if orientation in ('LOCAL', 'CURSOR') else axis_vec
            dot = self._get_dot(camera_pos, origin, axis_world, view_direction, use_perspective)
            alpha_mult = self._get_alpha_mult(dot)
            arrow_m = axis_matrices[tag].to_4x4()
            if orientation == 'LOCAL' and obj:
                rot_mat = obj.matrix_world.to_3x3().normalized().to_4x4()
                arrow_m = rot_mat @ arrow_m
            elif orientation == 'CURSOR':
                rot_mat = context.scene.cursor.rotation_euler.to_matrix().to_4x4()
                arrow_m = rot_mat @ arrow_m
            arrow_m.translation = origin
            gz_arrow.matrix_basis = arrow_m
            color = arrow_colors[idx]
            highlight_color = arrow_highlights[idx]
            gz_arrow.color = color[:3]
            gz_arrow.alpha = color[3] * alpha_mult
            gz_arrow.color_highlight = lighter(highlight_color, 0.5)[:3]
            gz_arrow.alpha_highlight = highlight_color[3]
            gz_arrow.hide = hide_mirror_gizmos
            self._update_highlight(gz_arrow, tag)

        for idx, (gz_box, tag) in enumerate(self.gizmos_boxes):
            axis, sign = tag[0].lower(), 1 if tag[1] == '+' else -1
            axis_vec = self._axis_vector(axis, sign)
            axis_world = mat @ axis_vec if orientation in ('LOCAL', 'CURSOR') else axis_vec
            dot = self._get_dot(camera_pos, origin, axis_world, view_direction, use_perspective)
            alpha_mult = self._get_alpha_mult(dot)
            box_m = axis_matrices[tag].to_4x4()
            if orientation == 'LOCAL' and context.active_object:
                rot_mat = context.active_object.matrix_world.to_3x3().normalized().to_4x4()
                box_m = rot_mat @ box_m
            elif orientation == 'CURSOR':
                rot_mat = context.scene.cursor.rotation_euler.to_matrix().to_4x4()
                box_m = rot_mat @ box_m
            box_m.translation = origin
            gz_box.matrix_basis = box_m
            box_color = getattr(addon.pref().theme.axis, ARROW_AXES[idx][1])
            gz_box.color = box_color[:3]
            gz_box.alpha = box_color[3] * alpha_mult
            gz_box.color_highlight = lighter(box_color, 0.5)[:3]
            gz_box.alpha_highlight = box_color[3]
            gz_box.hide_select = hide_mirror_gizmos
            self._update_highlight(gz_box, tag)

    def _get_origin(self, context, pivot):
        if pivot == 'WORLD':
            return Vector((0, 0, 0))
        elif pivot == 'ACTIVE' and context.active_object:
            return context.active_object.matrix_world.translation
        elif pivot == 'CURSOR':
            return context.scene.cursor.location
        elif context.active_object:
            return context.active_object.matrix_world.translation
        return Vector((0, 0, 0))

    def _get_orientation_matrix(self, context, orientation):
        if orientation == 'GLOBAL':
            return Matrix.Identity(3)
        elif orientation == 'LOCAL' and context.active_object:
            return context.active_object.matrix_world.to_3x3().normalized()
        elif orientation == 'CURSOR':
            return context.scene.cursor.rotation_euler.to_matrix()
        return Matrix.Identity(3)

    def _get_camera_info(self, context, origin):
        rv3d = context.region_data
        if rv3d:
            view_matrix_inv = rv3d.view_matrix.inverted()
            view_direction = -view_matrix_inv.col[2].to_3d().normalized()
            if rv3d.is_perspective:
                camera_pos = view_matrix_inv.translation
                use_perspective = True
            else:
                camera_pos = Vector((0, 0, 0))
                use_perspective = False
        else:
            camera_pos = Vector((0, 0, 0))
            view_direction = Vector((0, 0, -1))
            use_perspective = True
        return camera_pos, view_direction, use_perspective

    def _get_axis_matrices(self):
        return {
            'X+': Matrix(([0, 0, 1], [0, 1, 0], [-1, 0, 0])),
            'X-': Matrix(([0, 0, -1], [0, 1, 0], [1, 0, 0])),
            'Y+': Matrix(([1, 0, 0], [0, 0, 1], [0, -1, 0])),
            'Y-': Matrix(([1, 0, 0], [0, 0, -1], [0, 1, 0])),
            'Z+': Matrix(([1, 0, 0], [0, 1, 0], [0, 0, 1])),
            'Z-': Matrix(([-1, 0, 0], [0, 1, 0], [0, 0, -1])),
        }

    def _axis_vector(self, axis: str, sign: int) -> Vector:
        if axis == 'x':
            return Vector((sign, 0, 0))
        elif axis == 'y':
            return Vector((0, sign, 0))
        return Vector((0, 0, sign))

    def _get_dot(self, camera_pos, origin, axis_world, view_direction, use_perspective):
        if use_perspective:
            to_camera = (camera_pos - origin).normalized()
            return to_camera.dot(axis_world)
        return -view_direction.dot(axis_world)

    def _get_alpha_mult(self, dot: float) -> float:
        fade_threshold = 0.985
        abs_dot = abs(dot)
        if abs_dot > fade_threshold:
            return 1.0 - ((abs_dot - fade_threshold) / (1.0 - fade_threshold))
        return 1.0

    def _update_highlight(self, gz, tag):
        if gz.is_highlight:
            if self.last_highlighted_tag != tag:
                self.last_highlighted_tag = tag
        elif self.last_highlighted_tag == tag:
            self.last_highlighted_tag = None



classes = (
    ROTOR_GGT_MirrorGizmoGroup,
)
