import bpy
from bpy.props import BoolProperty, CollectionProperty, IntProperty
from ..utils import addon
from .mirror_utils import (
    MIRROR_AXIS_TRANSITIONS,
    toggle_axis,
    get_mirror_object,
    create_mirror_modifier,
    bisect_object,
)
from .mirror_props import ROTOR_PG_MirrorObjectItem


class ROTOR_OT_SetMirrorAxis(bpy.types.Operator):
    """Mirror axis"""

    bl_idname = "rotor.set_mirror_axis"
    bl_label = "Rotor Mirror Axis"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis to toggle",
        items=[("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")],
    )
    sign: bpy.props.EnumProperty(
        name="Sign",
        description="Sign (+ or -)",
        items=[("POS", "+", ""), ("NEG", "-", "")],
    )

    affected_objects: CollectionProperty(type=ROTOR_PG_MirrorObjectItem)
    active_object_index: IntProperty(name="Active Object", default=0)
    is_disabling: BoolProperty(name="Is Disabling", default=False)

    def invoke(self, context, event):
        """Populate the list when operator is invoked"""
        # Clear and populate the list with current selection
        self.affected_objects.clear()
        active_object = context.active_object
        objects_without_modifiers = 0

        # Check if we're enabling or disabling based on active object
        axis_idx = {"X": 0, "Y": 1, "Z": 2}[self.axis]
        is_neg = self.sign == "NEG"
        is_disabling = False

        # Only check active object if it's selected
        # Only check PINNED modifiers since set operation only affects pinned modifiers
        if (
            active_object
            and active_object.type == "MESH"
            and active_object.select_get()
        ):
            # Only look for pinned mirror modifiers for set operations
            active_mirror_mod = next(
                (
                    m
                    for m in reversed(active_object.modifiers)
                    if m.type == "MIRROR" and m.use_pin_to_last
                ),
                None,
            )
            if active_mirror_mod:
                # Check if we're trying to disable the axis on the pinned modifier
                current_state = (
                    active_mirror_mod.use_axis[axis_idx],
                    active_mirror_mod.use_bisect_flip_axis[axis_idx],
                    is_neg,
                )
                new_axis, _ = MIRROR_AXIS_TRANSITIONS[current_state]
                is_disabling = active_mirror_mod.use_axis[axis_idx] and not new_axis

        # Add active object first if it's a mesh and selected
        if (
            active_object
            and active_object.type == "MESH"
            and active_object.select_get()
        ):
            item = self.affected_objects.add()
            item.name = active_object.name
            item.enabled = True
            # Check if it has a mirror modifier
            has_mirror = any(m.type == "MIRROR" for m in active_object.modifiers)
            item.has_mirror_modifier = has_mirror
            if not has_mirror:
                objects_without_modifiers += 1

        # Add other selected objects (excluding active if already added)
        for obj in context.selected_objects:
            if obj.type == "MESH" and (not active_object or obj != active_object):
                # Skip if this is the active object and we already added it
                if active_object and obj == active_object:
                    continue
                item = self.affected_objects.add()
                item.name = obj.name
                item.enabled = True
                # Check if it has a mirror modifier
                has_mirror = any(m.type == "MIRROR" for m in obj.modifiers)
                item.has_mirror_modifier = has_mirror
                if not has_mirror:
                    objects_without_modifiers += 1

        # Store is_disabling state for use in draw methods
        self.is_disabling = is_disabling

        # Only show warning if we're disabling and objects don't have modifiers
        if is_disabling and objects_without_modifiers > 0:
            self.report(
                {"WARNING"},
                f"Cannot disable mirror on {objects_without_modifiers} objects without mirror modifiers.",
            )

        # Continue with normal execution
        return self.execute(context)

    def draw(self, context):
        """Draw checkboxes in the undo panel"""
        # context is required by Blender's API even if not used
        layout = self.layout

        if hasattr(self, "affected_objects") and self.affected_objects:
            # Use the stored is_disabling state
            is_disabling = self.is_disabling

            # Count objects with and without modifiers
            objects_with_modifiers = sum(
                1 for item in self.affected_objects if item.has_mirror_modifier
            )
            objects_without_modifiers = (
                len(self.affected_objects) - objects_with_modifiers
            )

            # Show object count
            if is_disabling and objects_without_modifiers > 0:
                layout.label(
                    text=f"Affected Objects: {objects_with_modifiers} (Cannot disable on {objects_without_modifiers} without modifiers)",
                    icon="ERROR",
                )
            elif not is_disabling and objects_without_modifiers > 0:
                layout.label(
                    text=f"Affected Objects: {len(self.affected_objects)} ({objects_without_modifiers} will get new modifiers)"
                )
            else:
                layout.label(text=f"Affected Objects: {len(self.affected_objects)}")

            # Use template_list for scrollable list
            layout.template_list(
                "ROTOR_UL_MirrorObjectList",
                "",
                self,
                "affected_objects",
                self,
                "active_object_index",
                rows=min(len(self.affected_objects), 10),  # Show up to 10 rows
                maxrows=10,
            )

    def execute(self, context):
        axis_map = {"X": 0, "Y": 1, "Z": 2}
        axis_idx = axis_map[self.axis]
        is_neg = self.sign == "NEG"

        active_object = context.active_object
        pref = addon.pref().tools.mirror
        pivot = pref.pivot
        orientation = pref.orientation

        # Track results
        affected_count = 0
        skipped_count = 0

        # First check active object to determine if we're enabling or disabling
        # Only check PINNED modifiers since set operation only affects pinned modifiers
        is_disabling = False
        if active_object and active_object.select_get():
            # Only look for pinned mirror modifiers for set operations
            active_mirror_mod = next(
                (
                    m
                    for m in reversed(active_object.modifiers)
                    if m.type == "MIRROR" and m.use_pin_to_last
                ),
                None,
            )

            if active_mirror_mod:
                # Check if we're trying to disable the axis on the pinned modifier
                current_state = (
                    active_mirror_mod.use_axis[axis_idx],
                    active_mirror_mod.use_bisect_flip_axis[axis_idx],
                    is_neg,
                )
                new_axis, _ = MIRROR_AXIS_TRANSITIONS[current_state]
                is_disabling = active_mirror_mod.use_axis[axis_idx] and not new_axis

        # Always calculate mirror object based on active object for consistency
        # This ensures all selected objects mirror relative to the same reference point
        mirror_object, individual = get_mirror_object(
            context, active_object, pivot, orientation
        )

        # Get list of enabled objects
        enabled_objects = []
        if hasattr(self, "affected_objects") and self.affected_objects:
            for item in self.affected_objects:
                if item.enabled and item.name in bpy.data.objects:
                    obj = bpy.data.objects[item.name]
                    if obj.type == "MESH":
                        enabled_objects.append(obj)
        else:
            # First run - use all selected mesh objects
            enabled_objects = [
                obj for obj in context.selected_objects if obj.type == "MESH"
            ]

        for obj in enabled_objects:
            # ONLY work with pinned mirror modifiers for set operation
            mirror_mod = next(
                (
                    m
                    for m in reversed(obj.modifiers)
                    if m.type == "MIRROR" and m.use_pin_to_last
                ),
                None,
            )

            if mirror_mod is None:
                if is_disabling:
                    # No pinned modifier to disable - skip this object
                    skipped_count += 1
                    continue
                else:
                    # Enabling - create a new pinned modifier
                    if pref.bisect:
                        bisect_object(
                            obj, axis_idx, pivot, orientation, context, is_neg
                        )

                    create_mirror_modifier(
                        context, obj, mirror_object, individual, axis_idx, is_neg
                    )
                    # Pin the newly created modifier for set operations
                    new_mod = next(
                        (m for m in reversed(obj.modifiers) if m.type == "MIRROR"), None
                    )
                    if new_mod:
                        new_mod.use_pin_to_last = True
                    affected_count += 1
                    continue

            # We have a pinned modifier - modify it
            use_axis = mirror_mod.use_axis
            use_bisect_flip = mirror_mod.use_bisect_flip_axis
            use_bisect = mirror_mod.use_bisect_axis

            toggle_axis(use_axis, use_bisect_flip, use_bisect, axis_idx, is_neg)

            # If all axes are disabled, remove the pinned modifier
            if not any(use_axis):
                obj.modifiers.remove(mirror_mod)

            affected_count += 1

        # Report results
        if is_disabling:
            if skipped_count > 0 and affected_count > 0:
                self.report(
                    {"WARNING"},
                    f"Disabled mirror on {affected_count} objects. Skipped {skipped_count} objects without pinned mirror modifiers.",
                )
            elif skipped_count > 0 and affected_count == 0:
                self.report(
                    {"ERROR"},
                    f"Could not disable mirror. {skipped_count} objects have no pinned mirror modifiers.",
                )
                return {"CANCELLED"}
            else:
                self.report({"INFO"}, f"Disabled mirror on {affected_count} objects.")
        else:
            # Enabling - we create modifiers if needed
            self.report({"INFO"}, f"Set mirror on {affected_count} objects.")

        # Check if we should return to previous tool
        pref = addon.pref().tools.mirror
        last_tool = context.scene.rotor.ops.last_tool
        if pref.tool_fallback and last_tool:
            # Check if we're currently using the mirror tool
            current_tool = context.workspace.tools.from_space_view3d_mode(
                context.mode, create=False
            )
            if current_tool and current_tool.idname == "rotor.mirror_tool":
                try:
                    bpy.ops.wm.tool_set_by_id(name=last_tool)
                    # Clear the last tool to prevent stale references
                    context.scene.rotor.ops.last_tool = ""
                except Exception:
                    # If switching fails, just continue
                    pass

        return {"FINISHED"}


classes = (ROTOR_OT_SetMirrorAxis,)
