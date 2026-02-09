import bpy
from mathutils import Matrix


class ROTOR_GGT_DuplicateGizmoGroup(bpy.types.GizmoGroup):
    """GizmoGroup for Rotor Duplicate Tool. Displays a move circle gizmo at each selected object's origin."""

    bl_idname = "ROTOR_GGT_DuplicateGizmoGroup"
    bl_label = "Rotor Duplicate Gizmo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D", "SHOW_MODAL_ALL"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gizmos_list = []

    @classmethod
    def poll(cls, context) -> bool:
        active_tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        )
        selected_objects = [
            obj for obj in context.selected_objects if obj.type == "MESH"
        ]
        return bool(
            active_tool
            and active_tool.idname == "rotor.duplicate_tool"
            and selected_objects
        )

    def setup(self, context):
        self.gizmos_list.clear()
        for obj in context.selected_objects:
            if obj.type != "MESH":
                continue
            gz = self.gizmos.new("GIZMO_GT_move_3d")
            gz.draw_style = "RING_2D"
            gz.color = (0.8, 0.8, 0.8)
            gz.alpha = 0.5
            gz.color_highlight = (1.0, 1.0, 1.0)
            gz.alpha_highlight = 0.8
            gz.scale_basis = 0.15
            gz.use_draw_modal = False
            mat = Matrix.Identity(4)
            mat.translation = obj.matrix_world.translation.copy()
            gz.matrix_basis = mat
            op = gz.target_set_operator("rotor.duplicate_modal")
            op.object_name = obj.name
            self.gizmos_list.append((gz, obj.name))

    def draw_prepare(self, context):
        rv3d = context.region_data
        view_rot = rv3d.view_matrix.to_3x3().inverted().to_4x4() if rv3d else Matrix.Identity(4)

        for gz, obj_name in self.gizmos_list:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                mat = view_rot.copy()
                mat.translation = obj.matrix_world.translation.copy()
                gz.matrix_basis = mat
            else:
                gz.hide = True


classes = (ROTOR_GGT_DuplicateGizmoGroup,)
