from math import pi

import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import intersect_line_plane
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

from ..utils import addon, infobar
from ..utils.operator import safe
from ..utils.scene import ray_cast
from ..shaders import handle
from ..shaders.draw import AXIS_DATA


def _snap_view(origin, region, rv3d, mouse_pos):
    """Project mouse onto a plane at origin facing the view."""
    ray_origin = region_2d_to_origin_3d(region, rv3d, mouse_pos)
    ray_dir = region_2d_to_vector_3d(region, rv3d, mouse_pos)

    if rv3d.is_perspective:
        view_normal = (ray_origin - origin).normalized()
    else:
        view_normal = -rv3d.view_matrix.inverted().col[2].to_3d().normalized()

    point = intersect_line_plane(
        ray_origin, ray_origin + ray_dir, origin, view_normal,
    )
    return point


def _raycast(context, mouse_pos, exclude):
    """Shared raycast helper that excludes the source object."""
    return ray_cast.visible(
        context, (mouse_pos.x, mouse_pos.y), exclude=exclude
    )


def _snap_origin(context, mouse_pos, exclude):
    """Raycast and snap to the hit object's origin."""
    ray = _raycast(context, mouse_pos, exclude)
    if ray.hit and ray.obj:
        return ray.obj.matrix_world.translation.copy()
    return None


def _snap_face(context, mouse_pos, exclude):
    """Raycast and snap to the hit point on the face."""
    ray = _raycast(context, mouse_pos, exclude)
    if ray.hit:
        return ray.location.copy()
    return None


def _snap_vertex(context, mouse_pos, exclude):
    """Raycast to face, then find closest vertex."""
    ray = _raycast(context, mouse_pos, exclude)
    if not ray.hit or not ray.obj:
        return None

    obj = ray.obj
    mesh = obj.data
    mat = obj.matrix_world

    if ray.index < 0 or ray.index >= len(mesh.polygons):
        return None

    poly = mesh.polygons[ray.index]
    hit_loc = ray.location

    closest_dist = float("inf")
    closest_point = None
    for vi in poly.vertices:
        world_co = mat @ mesh.vertices[vi].co
        dist = (world_co - hit_loc).length_squared
        if dist < closest_dist:
            closest_dist = dist
            closest_point = world_co

    return closest_point


def _snap_edge(context, mouse_pos, exclude):
    """Raycast to face, then find closest edge point."""
    ray = _raycast(context, mouse_pos, exclude)
    if not ray.hit or not ray.obj:
        return None

    obj = ray.obj
    mesh = obj.data
    mat = obj.matrix_world

    if ray.index < 0 or ray.index >= len(mesh.polygons):
        return None

    poly = mesh.polygons[ray.index]
    hit_loc = ray.location
    verts = poly.vertices

    closest_dist = float("inf")
    closest_point = None
    for i in range(len(verts)):
        a = mat @ mesh.vertices[verts[i]].co
        b = mat @ mesh.vertices[verts[(i + 1) % len(verts)]].co
        point = _closest_point_on_segment(hit_loc, a, b)
        dist = (point - hit_loc).length_squared
        if dist < closest_dist:
            closest_dist = dist
            closest_point = point

    return closest_point


def _snap_edge_center(context, mouse_pos, exclude):
    """Raycast to face, find closest edge, return its midpoint."""
    ray = _raycast(context, mouse_pos, exclude)
    if not ray.hit or not ray.obj:
        return None

    obj = ray.obj
    mesh = obj.data
    mat = obj.matrix_world

    if ray.index < 0 or ray.index >= len(mesh.polygons):
        return None

    poly = mesh.polygons[ray.index]
    hit_loc = ray.location
    verts = poly.vertices

    closest_dist = float("inf")
    closest_mid = None
    for i in range(len(verts)):
        a = mat @ mesh.vertices[verts[i]].co
        b = mat @ mesh.vertices[verts[(i + 1) % len(verts)]].co
        mid = (a + b) * 0.5
        point = _closest_point_on_segment(hit_loc, a, b)
        dist = (point - hit_loc).length_squared
        if dist < closest_dist:
            closest_dist = dist
            closest_mid = mid

    return closest_mid


def _snap_face_center(context, mouse_pos, exclude):
    """Raycast and snap to the hit face's center."""
    ray = _raycast(context, mouse_pos, exclude)
    if not ray.hit or not ray.obj:
        return None

    obj = ray.obj
    mesh = obj.data
    mat = obj.matrix_world

    if ray.index < 0 or ray.index >= len(mesh.polygons):
        return None

    poly = mesh.polygons[ray.index]
    return mat @ poly.center


def _closest_point_on_segment(point, a, b):
    """Return the closest point on segment a-b to point."""
    ab = b - a
    t = (point - a).dot(ab) / ab.dot(ab)
    t = max(0.0, min(1.0, t))
    return a + ab * t


_SNAP_FUNCTIONS = {
    "ORIGIN": _snap_origin,
    "FACE": _snap_face,
    "VERTEX": _snap_vertex,
    "EDGE": _snap_edge,
    "EDGE_CENTER": _snap_edge_center,
    "FACE_CENTER": _snap_face_center,
}

_MODE_CYCLE = ("LINEAR", "CIRCLE")
_PIVOT_CYCLE = ("INCREMENT", "GRID", "ORIGIN", "FACE", "VERTEX", "EDGE", "EDGE_CENTER", "FACE_CENTER")
_ORIENTATION_CYCLE = ("GLOBAL", "LOCAL")


class ROTOR_OT_DuplicateModal(bpy.types.Operator):
    """Duplicate object with visual guide"""

    bl_idname = "rotor.duplicate_modal"
    bl_label = "Rotor Duplicate"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    object_name: bpy.props.StringProperty(
        name="Object",
        description="Name of the object to duplicate",
    )
    count: bpy.props.IntProperty(
        name="Count",
        description="Number of duplicates",
        default=1,
        min=1,
    )
    dup_scale: bpy.props.FloatProperty(
        name="Scale",
        description="Scale factor for duplicates",
        default=1.0,
        min=0.01,
        max=10.0,
    )
    location: bpy.props.FloatVectorProperty(
        name="Location",
        description="Target placement point",
        subtype="XYZ",
    )
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[("LINEAR", "Linear", ""), ("CIRCLE", "Circle", "")],
        default="LINEAR",
    )
    axis_x: bpy.props.BoolProperty(name="X")
    axis_y: bpy.props.BoolProperty(name="Y")
    axis_z: bpy.props.BoolProperty(name="Z")
    double: bpy.props.BoolProperty(name="Double")
    align: bpy.props.BoolProperty(name="Align")
    orientation: bpy.props.EnumProperty(
        name="Orientation",
        items=[("GLOBAL", "Global", ""), ("LOCAL", "Local", "")],
        default="GLOBAL",
    )

    def invoke(self, context, event):
        obj = bpy.data.objects.get(self.object_name) if self.object_name else None
        if not obj:
            obj = context.active_object
        if not obj:
            self.report({"WARNING"}, "No object found")
            return {"CANCELLED"}

        self._exclude = {obj}
        self._selection = [o for o in context.selected_objects]
        self._origin = obj.matrix_world.translation.copy()
        self._origins = [o.matrix_world.translation.copy() for o in self._selection]
        self._local_rot = obj.matrix_world.to_3x3().normalized()
        self._last_point = None
        self._guide = handle.Guide()
        self._guide.create(context)
        self._ghost = handle.Ghost()
        self._ghost.create(context, obj)
        infobar.draw(context, event, self._infobar, blank=True)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    @safe
    def modal(self, context, event):
        context.area.tag_redraw()
        infobar.draw(context, event, self._infobar, blank=True)
        dup = addon.pref().tools.duplicate
        self._update_header(context, dup)

        if event.type in {"X", "Y", "Z"} and event.value == "PRESS":
            attr = f"axis_{event.type.lower()}"
            setattr(dup, attr, not getattr(dup, attr))
            return {"RUNNING_MODAL"}

        if event.type == "N" and event.value == "PRESS":
            dup.axis_x = False
            dup.axis_y = False
            dup.axis_z = False
            return {"RUNNING_MODAL"}

        if event.type == "C" and event.value == "PRESS":
            cur = _MODE_CYCLE.index(dup.mode)
            dup.mode = _MODE_CYCLE[(cur + 1) % len(_MODE_CYCLE)]
            return {"RUNNING_MODAL"}

        if event.type == "O" and event.value == "PRESS":
            cur = _ORIENTATION_CYCLE.index(dup.snap.orientation)
            dup.snap.orientation = _ORIENTATION_CYCLE[(cur + 1) % len(_ORIENTATION_CYCLE)]
            return {"RUNNING_MODAL"}

        if event.type == "P" and event.value == "PRESS":
            cur = _PIVOT_CYCLE.index(dup.snap.pivot)
            dup.snap.pivot = _PIVOT_CYCLE[(cur + 1) % len(_PIVOT_CYCLE)]
            return {"RUNNING_MODAL"}

        if event.type == "RIGHT_BRACKET" and event.value == "PRESS":
            dup.count += 1
            return {"RUNNING_MODAL"}

        if event.type == "LEFT_BRACKET" and event.value == "PRESS":
            if dup.count > 1:
                dup.count -= 1
            return {"RUNNING_MODAL"}

        if event.type == "QUOTE" and event.value == "PRESS":
            step = 0.01 if event.shift else 0.1
            dup.scale = round(dup.scale + step, 2)
            return {"RUNNING_MODAL"}

        if event.type == "SEMI_COLON" and event.value == "PRESS":
            step = 0.01 if event.shift else 0.1
            dup.scale = max(0.01, round(dup.scale - step, 2))
            return {"RUNNING_MODAL"}

        if event.type == "D" and event.value == "PRESS":
            dup.double = not dup.double
            return {"RUNNING_MODAL"}

        if event.type == "A" and event.value == "PRESS":
            dup.align = not dup.align
            return {"RUNNING_MODAL"}

        if event.type == "MOUSEMOVE":
            point = self._snap(context, event)
            if point:
                self._last_point = point
                rot = self._local_rot if dup.snap.orientation == "LOCAL" else None
                is_circle = dup.mode == "CIRCLE"
                self._guide.callback.update(
                    self._origin, point,
                    axis_x=dup.axis_x, axis_y=dup.axis_y, axis_z=dup.axis_z,
                    orientation=rot,
                    double=dup.double and not is_circle,
                    circle=is_circle,
                )
                self._ghost.callback.update(
                    self._ghost_positions(point, dup, context)
                )

        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._cancel(context)
            return {"CANCELLED"}

        if ((event.type == "LEFTMOUSE" and event.value == "RELEASE")
                or (event.type in {"SPACE", "RET"} and event.value == "PRESS")):
            self._finish(context)
            return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def _infobar(self, layout, context, event):
        """Draw the infobar hotkeys for the duplicate modal."""
        factor = 4.0
        row = layout.row(align=True)

        row.label(text="", icon="MOUSE_MOVE")
        row.label(text="Place")
        row.separator(factor=factor)
        row.label(text="Confirm", icon="MOUSE_LMB")
        row.separator(factor=factor)
        row.label(text="Cancel", icon="MOUSE_RMB")
        row.separator(factor=factor)
        row.label(text="Mode", icon="EVENT_C")
        row.separator(factor=factor)
        row.label(text="Axis", icon="EVENT_X")
        row.separator(factor=factor)
        row.label(text="Clear Axis", icon="EVENT_N")
        row.separator(factor=factor)
        row.label(text="[ ]  Count")
        row.separator(factor=factor)
        row.label(text="; '  Scale")
        row.separator(factor=factor)
        row.label(text="Orientation", icon="EVENT_O")
        row.separator(factor=factor)
        row.label(text="Snap", icon="EVENT_P")
        row.separator(factor=factor)
        row.label(text="Double", icon="EVENT_D")
        row.separator(factor=factor)
        row.label(text="Align", icon="EVENT_A")
        row.separator(factor=factor)

    def _update_header(self, context, dup):
        """Update the header with live values."""
        axes = []
        if dup.axis_x:
            axes.append("X")
        if dup.axis_y:
            axes.append("Y")
        if dup.axis_z:
            axes.append("Z")
        axis_text = ", ".join(axes) if axes else "Free"

        parts = [
            f"Mode: {dup.mode.capitalize()}",
            f"Count: {dup.count}",
            f"Scale: {dup.scale:.2f}",
            f"Axis: {axis_text}",
            f"Orientation: {dup.snap.orientation.capitalize()}",
            f"Snap: {dup.snap.pivot.replace('_', ' ').capitalize()}",
        ]
        if dup.mode == "LINEAR" and dup.double:
            parts.append("Double: On")
        if dup.mode == "CIRCLE" and dup.align:
            parts.append("Align: On")

        context.area.header_text_set(text="    ".join(parts))

    def _snap(self, context, event):
        region = context.region
        rv3d = context.region_data
        mouse = Vector((event.mouse_region_x, event.mouse_region_y))

        use_snap = context.tool_settings.use_snap != event.ctrl
        pivot = addon.pref().tools.duplicate.snap.pivot
        point = None

        if use_snap and pivot not in {"INCREMENT", "GRID"}:
            snap_fn = _SNAP_FUNCTIONS.get(pivot)
            point = snap_fn(context, mouse, self._exclude) if snap_fn else None

            # Raycast may deselect objects — restore selection
            for obj in self._selection:
                if not obj.select_get():
                    obj.select_set(True)

        if point is None:
            point = _snap_view(self._origin, region, rv3d, mouse)

        if use_snap and point:
            if pivot == "INCREMENT":
                point = self._snap_increment(context, point)
            elif pivot == "GRID":
                point = self._snap_grid(context, point)

        return point

    @staticmethod
    def _grid_step(context):
        overlay = context.space_data.overlay
        return overlay.grid_scale / overlay.grid_subdivisions

    def _snap_increment(self, context, point):
        """Snap the offset from origin to the nearest grid increment."""
        step = self._grid_step(context)
        offset = point - self._origin
        for i in range(3):
            offset[i] = round(offset[i] / step) * step
        return self._origin + offset

    @staticmethod
    def _snap_grid(context, point):
        """Snap the absolute position to the nearest grid line."""
        step = ROTOR_OT_DuplicateModal._grid_step(context)
        snapped = point.copy()
        for i in range(3):
            snapped[i] = round(point[i] / step) * step
        return snapped

    def _ghost_offsets(self, point, dup):
        """Compute direction offsets from grabbed object's origin."""
        diff = point - self._origin
        any_axis = dup.axis_x or dup.axis_y or dup.axis_z
        is_circle = dup.mode == "CIRCLE"
        factor = 1.0 if is_circle else (2.0 if dup.double else 1.0)
        offsets = []
        if not any_axis:
            offsets.append(diff * factor)
        else:
            r = self._local_rot if dup.snap.orientation == "LOCAL" else Matrix.Identity(3)
            for name, enabled in [("x", dup.axis_x), ("y", dup.axis_y), ("z", dup.axis_z)]:
                if not enabled:
                    continue
                d = r @ AXIS_DATA[name][0]
                offsets.append(d * factor * diff.dot(d))
        return offsets

    @staticmethod
    def _view_normal(context):
        rv3d = context.region_data
        return -rv3d.view_matrix.inverted().col[2].to_3d().normalized()

    def _circle_axes(self, dup, context):
        """Return rotation axes for circle mode based on axis constraints."""
        any_axis = dup.axis_x or dup.axis_y or dup.axis_z
        if not any_axis:
            return [self._view_normal(context)]
        r = self._local_rot if dup.snap.orientation == "LOCAL" else Matrix.Identity(3)
        axes = []
        for name, enabled in [("x", dup.axis_x), ("y", dup.axis_y), ("z", dup.axis_z)]:
            if not enabled:
                continue
            axes.append(r @ AXIS_DATA[name][0])
        return axes

    @staticmethod
    def _apply_circle_align(obj, angle, axis):
        """Rotate obj by *angle* around *axis*, composing with its current rotation."""
        circle_quat = Matrix.Rotation(angle, 3, axis).to_quaternion()
        mode = obj.rotation_mode
        if mode == 'QUATERNION':
            obj.rotation_quaternion = circle_quat @ obj.rotation_quaternion
        elif mode == 'AXIS_ANGLE':
            aa = obj.rotation_axis_angle
            base = Matrix.Rotation(aa[0], 3, Vector(aa[1:])).to_quaternion()
            result = circle_quat @ base
            ax, ang = result.to_axis_angle()
            obj.rotation_axis_angle = (ang, *ax)
        else:
            base = obj.rotation_euler.to_quaternion()
            result = circle_quat @ base
            obj.rotation_euler = result.to_euler(mode)

    def _ghost_positions(self, point, dup, context):
        """Compute ghost placements (position, scale, rotation) for current mode."""
        count = dup.count
        scale = dup.scale
        align = dup.align
        placements = []

        if dup.mode == "CIRCLE":
            diff = point - self._origin
            rot_axes = self._circle_axes(dup, context)
            for org in self._origins:
                center = org + diff
                radius = -diff
                for axis in rot_axes:
                    for i in range(1, count + 1):
                        angle = 2 * pi * i / (count + 1)
                        rot = Matrix.Rotation(angle, 3, axis)
                        pos = center + rot @ radius
                        ghost_rot = rot if align else None
                        placements.append((pos, scale, ghost_rot))
        else:
            offsets = self._ghost_offsets(point, dup)
            any_axis = dup.axis_x or dup.axis_y or dup.axis_z
            for org in self._origins:
                for offset in offsets:
                    for i in range(1, count + 1):
                        t = i / count
                        s = 1.0 + (scale - 1.0) * t
                        pos = org + offset * t
                        placements.append((pos, s, None))
        return placements

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "count")
        layout.prop(self, "dup_scale")
        layout.prop(self, "align")
        col = layout.column(align=True)
        col.prop(self, "location")

    def execute(self, context):
        self._create_duplicates(context)
        return {"FINISHED"}

    def _finish(self, context):
        """Copy modal state to operator properties, clean up, create duplicates."""
        context.area.header_text_set(text=None)
        infobar.remove(context)
        self._guide.remove()
        self._ghost.remove()
        if not self._last_point:
            context.area.tag_redraw()
            return

        dup = addon.pref().tools.duplicate
        self.count = dup.count
        self.dup_scale = dup.scale
        self.location = self._last_point
        self.mode = dup.mode
        self.axis_x = dup.axis_x
        self.axis_y = dup.axis_y
        self.axis_z = dup.axis_z
        self.double = dup.double
        self.align = dup.align
        self.orientation = dup.snap.orientation

        self._create_duplicates(context)
        context.area.tag_redraw()

    def _create_duplicates(self, context):
        """Create duplicate objects using operator properties."""
        obj = bpy.data.objects.get(self.object_name) if self.object_name else context.active_object
        if not obj:
            return

        selection = list(context.selected_objects)
        if not selection:
            selection = [obj]

        origin = obj.matrix_world.translation.copy()
        local_rot = obj.matrix_world.to_3x3().normalized()
        point = Vector(self.location)
        count = self.count
        scale = self.dup_scale
        is_circle = self.mode == "CIRCLE"
        any_axis = self.axis_x or self.axis_y or self.axis_z

        new_objects = []
        if is_circle:
            diff = point - origin
            if not any_axis:
                rv3d = context.region_data
                if rv3d:
                    rot_axes = [-rv3d.view_matrix.inverted().col[2].to_3d().normalized()]
                else:
                    rot_axes = [Vector((0, 0, 1))]
            else:
                r = local_rot if self.orientation == "LOCAL" else Matrix.Identity(3)
                rot_axes = []
                for name, enabled in [("x", self.axis_x), ("y", self.axis_y), ("z", self.axis_z)]:
                    if enabled:
                        rot_axes.append(r @ AXIS_DATA[name][0])

            for sel_obj in selection:
                org = sel_obj.matrix_world.translation
                center = org + diff
                radius = -diff
                for axis in rot_axes:
                    for i in range(1, count + 1):
                        angle = 2 * pi * i / (count + 1)
                        rot = Matrix.Rotation(angle, 3, axis)
                        pos = center + rot @ radius

                        new_obj = sel_obj.copy()
                        new_obj.data = sel_obj.data.copy()
                        for col in sel_obj.users_collection:
                            col.objects.link(new_obj)
                        new_obj.location = pos
                        new_obj.scale = sel_obj.scale * scale
                        if self.align:
                            self._apply_circle_align(new_obj, angle, axis)
                        new_objects.append(new_obj)
        else:
            diff = point - origin
            factor = 2.0 if self.double else 1.0
            offsets = []
            if not any_axis:
                offsets.append(diff * factor)
            else:
                r = local_rot if self.orientation == "LOCAL" else Matrix.Identity(3)
                for name, enabled in [("x", self.axis_x), ("y", self.axis_y), ("z", self.axis_z)]:
                    if enabled:
                        d = r @ AXIS_DATA[name][0]
                        offsets.append(d * factor * diff.dot(d))

            for sel_obj in selection:
                org = sel_obj.matrix_world.translation
                for offset in offsets:
                    for i in range(1, count + 1):
                        t = i / count
                        s = 1.0 + (scale - 1.0) * t
                        pos = org + offset * t

                        new_obj = sel_obj.copy()
                        new_obj.data = sel_obj.data.copy()
                        for col in sel_obj.users_collection:
                            col.objects.link(new_obj)
                        new_obj.location = pos
                        new_obj.scale = sel_obj.scale * s
                        new_objects.append(new_obj)

        for sel_obj in selection:
            sel_obj.select_set(False)
        for new_obj in new_objects:
            new_obj.select_set(True)
        if new_objects:
            context.view_layer.objects.active = new_objects[0]

    def _cancel(self, context):
        context.area.header_text_set(text=None)
        infobar.remove(context)
        self._guide.remove()
        self._ghost.remove()
        context.area.tag_redraw()


classes = (ROTOR_OT_DuplicateModal,)
