import bpy
from mathutils import Vector, Matrix

from ..utils import addon


AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}


def _axis_unit(axis: str) -> Vector:
    v = Vector((0, 0, 0))
    v[AXIS_INDEX[axis]] = 1.0
    return v


def _bbox_extreme(obj, axis_world: Vector, sign: int) -> Vector:
    """Return the world-space bbox corner whose projection onto axis_world is
    extreme in the given sign direction."""
    mat = obj.matrix_world
    corners = [mat @ Vector(c) for c in obj.bound_box]
    if sign >= 0:
        return max(corners, key=lambda c: c.dot(axis_world))
    return min(corners, key=lambda c: c.dot(axis_world))


class ROTOR_OT_AlignAxis(bpy.types.Operator):
    """Align selected objects to a target along a chosen axis"""

    bl_idname = "mirror.align_axis"
    bl_label = "Align Axis"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    target: bpy.props.EnumProperty(
        name="Target",
        items=[
            ("WORLD", "World", "Align to world origin"),
            ("ACTIVE", "Active", "Align to active object"),
            ("CURSOR", "Cursor", "Align to 3D cursor"),
        ],
        default="WORLD",
    )
    axis: bpy.props.EnumProperty(
        name="Axis",
        items=[("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")],
        default="X",
    )
    sign: bpy.props.EnumProperty(
        name="Sign",
        items=[("POS", "+", ""), ("NEG", "-", "")],
        default="POS",
    )

    @classmethod
    def poll(cls, context):
        return any(o.type == "MESH" for o in context.selected_objects)

    def execute(self, context):
        active = context.active_object
        pref = addon.pref().tools.align
        orientation = pref.orientation
        source = pref.source
        target_source = pref.target_source
        cursor = context.scene.cursor

        # LOCAL orientation uses the target's own rotation frame:
        # ACTIVE → active object's matrix, CURSOR → cursor's matrix. WORLD
        # has no rotation so LOCAL collapses to GLOBAL there.
        if orientation == "LOCAL":
            if self.target == "ACTIVE" and active:
                rot_mat = active.matrix_world.to_3x3().normalized()
            elif self.target == "CURSOR":
                rot_mat = cursor.matrix.to_3x3()
            else:
                rot_mat = Matrix.Identity(3)
        else:
            rot_mat = Matrix.Identity(3)

        axis_world = (rot_mat @ _axis_unit(self.axis)).normalized()
        # The arrow on the +X side puts the moving object's -X face at the
        # target (the face nearest the target) and uses the target's +X face
        # (the face the moving object butts against). The two bbox-face signs
        # are therefore opposite.
        bbox_sign_mover = -1 if self.sign == "POS" else 1
        bbox_sign_target = -bbox_sign_mover

        if self.target == "ACTIVE":
            if not active:
                self.report({"WARNING"}, "No active object")
                return {"CANCELLED"}
            if target_source == "BBOX":
                target_point = _bbox_extreme(active, axis_world, bbox_sign_target)
            else:
                target_point = active.matrix_world.translation
        elif self.target == "CURSOR":
            target_point = cursor.location.copy()
        else:
            target_point = Vector((0, 0, 0))

        target_value = target_point.dot(axis_world)

        movers = []
        for obj in context.selected_objects:
            if obj.type != "MESH":
                continue
            if self.target == "ACTIVE" and obj == active:
                continue
            movers.append(obj)

        if not movers:
            self.report({"WARNING"}, "No objects to align")
            return {"CANCELLED"}

        moved = 0
        for obj in movers:
            if source == "BBOX":
                src_point = _bbox_extreme(obj, axis_world, bbox_sign_mover)
            else:
                src_point = obj.matrix_world.translation
            src_value = src_point.dot(axis_world)
            delta = (target_value - src_value) * axis_world
            if delta.length_squared > 0.0:
                obj.matrix_world.translation = obj.matrix_world.translation + delta
            moved += 1

        self.report({"INFO"}, f"Aligned {moved} object{'s' if moved != 1 else ''}")

        # Tool fallback
        pref = addon.pref().tools.align
        last_tool = context.scene.rotor.ops.last_tool
        if pref.tool_fallback and last_tool:
            current_tool = context.workspace.tools.from_space_view3d_mode(
                context.mode, create=False
            )
            if current_tool and current_tool.idname == "mirror.align_tool":
                try:
                    bpy.ops.wm.tool_set_by_id(name=last_tool)
                    context.scene.rotor.ops.last_tool = ""
                except Exception:
                    pass

        return {"FINISHED"}


classes = (ROTOR_OT_AlignAxis,)
