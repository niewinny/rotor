import bmesh
import bpy

from ..utils import addon
from .mirror_mesh_utils import get_mesh_mirror_frame, symmetrize_geom


class ROTOR_OT_MirrorMesh(bpy.types.Operator):
    """Mirror (symmetrize) mesh geometry across the gizmo plane"""

    bl_idname = "mirror.mirror_mesh"
    bl_label = "Mirror Mesh"
    bl_options = {"REGISTER", "UNDO"}

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis to mirror across",
        items=[("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")],
    )
    sign: bpy.props.EnumProperty(
        name="Sign",
        description="Side to keep as the source of the mirror",
        items=[("POS", "+", ""), ("NEG", "-", "")],
    )
    target: bpy.props.EnumProperty(
        name="Target",
        description="Geometry to mirror",
        items=[
            ("SELECTION", "Selection", "Mirror only the selected geometry"),
            ("MESH", "Mesh", "Mirror the full mesh"),
        ],
        default="SELECTION",
    )

    @classmethod
    def description(cls, context, properties):
        if properties.target == "MESH":
            return "Mirror the full mesh across the gizmo plane"
        return "Mirror the selected mesh across the gizmo plane"

    @classmethod
    def poll(cls, context):
        return (
            context.mode == "EDIT_MESH"
            and context.edit_object is not None
            and context.edit_object.type == "MESH"
        )

    def execute(self, context):
        obj = context.edit_object
        pref = addon.pref().tools.mesh

        frame_data = get_mesh_mirror_frame(context)
        if frame_data is None:
            self.report({"WARNING"}, "Select geometry to define the mirror plane.")
            return {"CANCELLED"}
        world_pivot, frame = frame_data

        axis_idx = {"X": 0, "Y": 1, "Z": 2}[self.axis]
        is_neg = self.sign == "NEG"
        if pref.reverse_controls:
            is_neg = not is_neg

        mw_inv = obj.matrix_world.inverted()
        world_axis = frame.col[axis_idx]
        if world_axis.length < 1e-6:
            self.report({"WARNING"}, "Degenerate mirror orientation.")
            return {"CANCELLED"}

        local_no = (mw_inv.to_3x3() @ world_axis).normalized()
        if is_neg:
            local_no = -local_no
        local_co = mw_inv @ world_pivot

        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.normal_update()

        if self.target == "MESH":
            verts, edges, faces = bm.verts[:], bm.edges[:], bm.faces[:]
            select_result = False
        else:
            verts = [v for v in bm.verts if v.select]
            edges = [e for e in bm.edges if e.select]
            faces = [f for f in bm.faces if f.select]
            select_result = True
            if not verts:
                self.report({"WARNING"}, "No selected geometry to mirror.")
                return {"CANCELLED"}

        symmetrize_geom(
            bm, verts, edges, faces, local_co, local_no,
            pref.merge, pref.merge_threshold, select_result,
        )

        if select_result:
            bm.select_flush(True)
        bmesh.update_edit_mesh(me)

        scope = "mesh" if self.target == "MESH" else "selection"
        self.report({"INFO"}, f"Mirrored {scope} across {self.axis}.")

        self._tool_fallback(context, pref)
        return {"FINISHED"}

    def _tool_fallback(self, context, pref):
        last_tool = context.scene.rotor.ops.last_tool
        if not (pref.tool_fallback and last_tool):
            return
        current_tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        )
        if current_tool and current_tool.idname == "mirror.mirror_mesh_tool":
            try:
                bpy.ops.wm.tool_set_by_id(name=last_tool)
                context.scene.rotor.ops.last_tool = ""
            except Exception:
                pass


classes = (ROTOR_OT_MirrorMesh,)
