"""Modal operator to interactively pick the Mirror tool's custom plane.

Aim at any visible mesh: the element under the cursor (vert/edge/face) is
highlighted and a preview (Z normal arrow + X/Y cross) shows where the plane
lands. Confirming writes the picked orientation/pivot into the active tool's
preference group and switches the matching enum(s) to ``CUSTOM``.

Works in both Object and Edit-mesh mode; the values are stored separately per
mode (``addon.pref().tools.mirror`` vs ``.mesh``). Tab cycles which part the
pick writes: Both / Orientation / Pivot. Modeled on blockout's Alt+Space picker.
"""

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from ..shaders import handle as handle_mod
from ..utils import addon
from ..utils.scene import ray_cast, snap

# Tab cycle order for the write target.
TARGET_ORDER = ("BOTH", "ORIENTATION", "PIVOT")
TARGET_LABEL = {
    "BOTH": "Orientation + Pivot",
    "ORIENTATION": "Orientation",
    "PIVOT": "Pivot",
}


class ROTOR_OT_PickCustomPlane(bpy.types.Operator):
    bl_idname = "mirror.pick_custom_plane"
    bl_label = "Pick Custom Plane"
    bl_description = (
        "Interactively set the custom orientation/pivot by snapping to geometry\n"
        " • Move mouse - snap to vert/edge/face under cursor\n"
        " • TAB - cycle Orientation+Pivot / Orientation / Pivot\n"
        " • LMB / SPACE - confirm\n"
        " • RMB / ESC - cancel"
    )
    bl_options = {"REGISTER"}

    target: bpy.props.EnumProperty(
        name="Target",
        description="Which part of the custom plane to set",
        items=[
            ("BOTH", "Orientation + Pivot", "Set both the custom orientation and pivot"),
            ("ORIENTATION", "Orientation", "Set the custom orientation only"),
            ("PIVOT", "Pivot", "Set the custom pivot only"),
        ],
        default="BOTH",
    )

    @classmethod
    def poll(cls, context):
        return context.mode in {"OBJECT", "EDIT_MESH"}

    def _group(self, context):
        tools = addon.pref().tools
        return tools.mesh if context.mode == "EDIT_MESH" else tools.mirror

    def _current_plane(self, context, group):
        """Current effective mirror plane (location, normal, direction) in world
        space, so a single-part pick keeps the *other* part at its real value
        (not a stale custom snapshot)."""
        if context.mode == "EDIT_MESH":
            from .mirror_mesh_utils import get_mesh_mirror_frame

            data = get_mesh_mirror_frame(context)
            if data is not None:
                world_pivot, frame = data
                return world_pivot.copy(), frame.col[2].copy(), frame.col[0].copy()
            mat = Euler(group.custom_rotation, "XYZ").to_matrix()
            return Vector(group.custom_location), mat.col[2].copy(), mat.col[0].copy()

        # Object mode: derive from the active pivot / orientation settings.
        obj = context.active_object
        if group.pivot == "WORLD":
            location = Vector((0.0, 0.0, 0.0))
        elif group.pivot == "CURSOR":
            location = context.scene.cursor.location.copy()
        elif group.pivot == "CUSTOM":
            location = Vector(group.custom_location)
        elif obj is not None:  # ACTIVE / INDIVIDUAL
            location = obj.matrix_world.translation.copy()
        else:
            location = Vector((0.0, 0.0, 0.0))

        if group.orientation == "LOCAL" and obj is not None:
            mat = obj.matrix_world.to_3x3().normalized()
        elif group.orientation == "CURSOR":
            mat = context.scene.cursor.rotation_euler.to_matrix()
        elif group.orientation == "CUSTOM":
            mat = Euler(group.custom_rotation, "XYZ").to_matrix()
        else:  # GLOBAL
            mat = Matrix.Identity(3)
        return location, mat.col[2].copy(), mat.col[0].copy()

    @staticmethod
    def _find_view3d(context):
        """Return (region, rv3d) of a 3D viewport WINDOW region.

        Prefers the active region (Space launch); otherwise finds the first
        VIEW_3D area so the popover Pick button works too.
        """
        if context.region and context.region.type == "WINDOW" and context.region_data:
            return context.region, context.region_data
        for area in context.screen.areas:
            if area.type != "VIEW_3D":
                continue
            rv3d = getattr(area.spaces.active, "region_3d", None)
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            if region and rv3d:
                return region, rv3d
        return None, None

    def _mouse(self, event):
        """Region-relative mouse from absolute coords (region-independent)."""
        return (event.mouse_x - self.region.x, event.mouse_y - self.region.y)

    def invoke(self, context, event):
        region, rv3d = self._find_view3d(context)
        if region is None or rv3d is None:
            self.report({"WARNING"}, "Must be run with a 3D viewport open.")
            return {"CANCELLED"}
        self.region = region
        self.rv3d = rv3d

        group = self._group(context)

        # Snapshot the current effective plane so a single-part pick keeps the
        # other part placed at its real current value.
        self.orig_location, self.orig_normal, self.orig_direction = self._current_plane(
            context, group
        )

        self._target = self.target
        self.preview = None  # (location, normal, direction) or None when no hit
        self.mouse = self._mouse(event)

        self._detected = None
        self._location = None

        self._setup_handlers(context)
        self._update_snap(context)

        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()

        if event.type == "MOUSEMOVE":
            self.mouse = self._mouse(event)
            self._update_snap(context)
            return {"RUNNING_MODAL"}

        if event.type == "TAB" and event.value == "PRESS":
            i = TARGET_ORDER.index(self._target)
            self._target = TARGET_ORDER[(i + 1) % len(TARGET_ORDER)]
            self._update_snap(context)
            return {"RUNNING_MODAL"}

        if event.type in {"LEFTMOUSE", "SPACE", "RET", "NUMPAD_ENTER"} and event.value == "PRESS":
            self._commit(context)
            self._cleanup(context)
            return {"FINISHED"}

        if event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            self._cleanup(context)
            return {"CANCELLED"}

        # No passthrough: consume every other event (including MMB navigation).
        return {"RUNNING_MODAL"}

    # --- snapping -----------------------------------------------------------

    def _update_snap(self, context):
        """Raycast under the cursor and rebuild the preview batch + header.

        Guarded as a whole: a degenerate hit must never crash the modal (which
        would abort it without cleanup and leak the draw handler).
        """
        self.preview = None
        self._detected = None
        self._location = None
        try:
            ray = ray_cast.visible(
                context, self.mouse, modes=("OBJECT", "EDIT"),
                region=self.region, rv3d=self.rv3d,
            )

            if ray.hit and ray.obj is not None:
                obj = ray.obj
                depsgraph = context.evaluated_depsgraph_get()
                obj_eval = obj.evaluated_get(depsgraph)
                me_eval = obj_eval.to_mesh()
                bm = bmesh.new()
                bm.from_mesh(me_eval)
                obj_eval.to_mesh_clear()
                bm.verts.ensure_lookup_table()
                bm.edges.ensure_lookup_table()
                bm.faces.ensure_lookup_table()

                try:
                    element_type, element = snap.find_closest_element(
                        context, obj, ray.location, ray.index, bm
                    )
                    location, normal, direction, _ = snap.element_plane(
                        obj.matrix_world, element_type, element, ray
                    )
                finally:
                    bm.free()
                    del obj_eval

                self._detected = element_type
                if self._target == "PIVOT":
                    self.preview = (location, self.orig_normal, self.orig_direction)
                elif self._target == "ORIENTATION":
                    self.preview = (self.orig_location, normal, direction)
                else:  # BOTH
                    self.preview = (location, normal, direction)
                self._location = self.preview[0]
        except Exception:
            self.preview = None
            self._detected = None
            self._location = None

        self._draw(context)
        self._update_header(context)

    # --- drawing ------------------------------------------------------------

    def _setup_handlers(self, context):
        self._preview_handle = handle_mod.PlanePreview()
        self._preview_handle.create(context)

    def _preview_size(self):
        rv3d = self.rv3d
        if rv3d and hasattr(rv3d, "view_distance"):
            return max(rv3d.view_distance * 0.06, 0.01)
        return 0.5

    def _draw(self, context):
        preview_cb = self._preview_handle.callback
        if self.preview is None:
            preview_cb.clear()
            return

        location, normal, direction = self.preview
        theme = addon.pref().theme.axis
        colors = (tuple(theme.x), tuple(theme.y), tuple(theme.z))
        preview_cb.update(location, normal, direction, self._preview_size(), colors)

    # --- commit / teardown --------------------------------------------------

    def _commit(self, context):
        if self.preview is None:
            return
        location, normal, direction = self.preview
        group = self._group(context)

        if self._target in {"ORIENTATION", "BOTH"}:
            group.custom_rotation = snap.rotation_from_vectors(normal, direction)
            group.orientation = "CUSTOM"
        if self._target in {"PIVOT", "BOTH"}:
            group.custom_location = location
            group.pivot = "CUSTOM"

    def _update_header(self, context):
        if not context.area:
            return
        if self._detected and self._location is not None:
            detected = self._detected.capitalize()
            loc = self._location
            location = f"({loc.x:.3f}, {loc.y:.3f}, {loc.z:.3f})"
        else:
            detected = "–"
            location = "–"
        context.area.header_text_set(
            f"Mode: {TARGET_LABEL[self._target]}      "
            f"Detected: {detected}      Location: {location}"
        )

    def _cleanup(self, context):
        if getattr(self, "_preview_handle", None):
            self._preview_handle.remove()
        if context.area:
            context.area.header_text_set(None)
            context.area.tag_redraw()


classes = (ROTOR_OT_PickCustomPlane,)
