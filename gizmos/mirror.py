import bpy
from mathutils import Vector, Matrix
from ..utils import addon

# Helper: axis info for 
alpha = 0.8
ARROW_AXES = [
    (Vector((1, 0, 0)), (1, 0, 0, alpha), 'X+'),   # Red +X
    (Vector((-1, 0, 0)), (1, 0, 0, alpha), 'X-'),  # Red -X
    (Vector((0, 1, 0)), (0, 1, 0, alpha), 'Y+'),   # Green +Y
    (Vector((0, -1, 0)), (0, 1, 0, alpha), 'Y-'),  # Green -Y
    (Vector((0, 0, 1)), (0, 0, 1, alpha), 'Z+'),   # Blue +Z
    (Vector((0, 0, -1)), (0, 0, 1, alpha), 'Z-'),  # Blue -Z
]


def create_arrow_gizmo(group, axis, color, idx):
    gz = group.gizmos.new("GIZMO_GT_arrow_3d")
    gz.color = color[:3]  # Use only RGB
    gz.alpha = color[3]   # Use alpha
    gz.color_highlight = color[:3]
    gz.alpha_highlight = color[3]
    gz.scale_basis = 1.0
    gz.use_draw_modal = True
    gz.hide_select = False
    gz.matrix_basis = Matrix.Identity(4)
    gz.draw_style = 'BOX'
    return gz


class ROTOR_GGT_MirrorGizmoGroup(bpy.types.GizmoGroup):
    bl_idname = "ROTOR_GGT_MirrorGizmoGroup"
    bl_label = "Rotor Mirror Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'SHOW_MODAL_ALL', 'SCALE'}


    @classmethod
    def poll(cls, context):
        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        mirror_tool = True if active_tool and active_tool.idname == 'rotor.mirror_tool' else False
        return mirror_tool

    def setup(self, context):
        self.gizmos_arrows = []  # Will hold (gizmo, tag)
        for idx, (axis, color, tag) in enumerate(ARROW_AXES):
            gz = create_arrow_gizmo(self, axis, color, tag)
            # Set up operator call for each arrow
            gz.target_set_operator("rotor.mirror_axis")
            self.gizmos_arrows.append((gz, tag))


    def draw_prepare(self, context):
        # Get preferences
        pref = addon.pref()
        mirror_tool = pref.tools.mirror
        orientation = getattr(mirror_tool, 'orientation', 'GLOBAL')
        pivot = getattr(mirror_tool, 'pivot', 'ACTIVE')

        # Determine origin
        if pivot == 'ACTIVE':
            origin = context.active_object.matrix_world.translation if context.active_object else Vector((0, 0, 0))
        else:  # INDIVIDUAL or fallback
            origin = context.active_object.matrix_world.translation if context.active_object else Vector((0, 0, 0))

        # Determine orientation
        if orientation == 'GLOBAL':
            mat = Matrix.Identity(3)
        elif orientation == 'LOCAL' and context.active_object:
            mat = context.active_object.matrix_world.to_3x3().normalized()
        else:
            mat = Matrix.Identity(3)

        def axis_matrix(axis, origin):
            up = axis.normalized()
            if abs(up.x) < 0.99:
                right = up.cross(Vector((1, 0, 0))).normalized()
            else:
                right = up.cross(Vector((0, 1, 0))).normalized()
            forward = right.cross(up).normalized()
            rot = Matrix((right, forward, up)).transposed().to_4x4()
            rot.translation = origin
            return rot

        # Update arrow gizmos to face correct direction
        for idx, (gz, tag) in enumerate(self.gizmos_arrows):
            axis_vec, _, _ = ARROW_AXES[idx]
            axis_world = mat @ axis_vec
            gz.matrix_basis = axis_matrix(axis_world, origin)

classes = (
    ROTOR_GGT_MirrorGizmoGroup,
)
