import bpy

class ROTOR_OT_SetMirrorAxis(bpy.types.Operator):
    """Set mirror axis"""
    bl_idname = "rotor.set_mirror_axis"
    bl_label = "Rotor Mirror Axis"
    bl_options = {'REGISTER', 'UNDO'}

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis to toggle",
        items=[('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')],
    )
    sign: bpy.props.EnumProperty(
        name="Sign",
        description="Sign (+ or -)",
        items=[('POS', '+', ''), ('NEG', '-', '')],
    )

    def execute(self, context):
        axis_map = {'X': 0, 'Y': 1, 'Z': 2}
        axis_idx = axis_map[self.axis]
        is_neg = self.sign == 'NEG'

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            # Find or create mirror modifier
            mirror_mod = None
            for mod in obj.modifiers:
                if mod.type == 'MIRROR':
                    mirror_mod = mod
            if not mirror_mod:
                mirror_mod = obj.modifiers.new(name="Mirror", type='MIRROR')
                # Immediately enable the pressed axis and sign
                mirror_mod.use_axis[axis_idx] = True
                mirror_mod.use_bisect_flip_axis[axis_idx] = is_neg
                # Always enable use_bisect_axis when use_axis is enabled
                if hasattr(mirror_mod, 'use_bisect_axis'):
                    mirror_mod.use_bisect_axis[axis_idx] = True
                continue  # Done for this object, no toggle logic needed
            # Toggle logic
            if not mirror_mod.use_axis[axis_idx]:
                # If axis is off, turn it on and set bisect
                mirror_mod.use_axis[axis_idx] = True
                mirror_mod.use_bisect_flip_axis[axis_idx] = is_neg
                if hasattr(mirror_mod, 'use_bisect_axis'):
                    mirror_mod.use_bisect_axis[axis_idx] = True
            else:
                # If axis is on, toggle bisect or turn off
                if is_neg:
                    if mirror_mod.use_bisect_flip_axis[axis_idx]:
                        # If already negative, turn off axis
                        mirror_mod.use_axis[axis_idx] = False
                        mirror_mod.use_bisect_flip_axis[axis_idx] = False
                    else:
                        # Switch to negative
                        mirror_mod.use_bisect_flip_axis[axis_idx] = True
                else:
                    if not mirror_mod.use_bisect_flip_axis[axis_idx]:
                        # If already positive, turn off axis
                        mirror_mod.use_axis[axis_idx] = False
                    else:
                        # Switch to positive
                        mirror_mod.use_bisect_flip_axis[axis_idx] = False
        return {'FINISHED'}


class ROTOR_OT_AddMirrorAxis(bpy.types.Operator):
    bl_idname = "rotor.add_mirror_axis"
    bl_label = "Rotor Mirror Axis"
    bl_options = {'REGISTER', 'UNDO'}

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis to toggle",
        items=[('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')],
    )
    sign: bpy.props.EnumProperty(
        name="Sign",
        description="Sign (+ or -)",
        items=[('POS', '+', ''), ('NEG', '-', '')],
    )

    def execute(self, context):
        axis_map = {'X': 0, 'Y': 1, 'Z': 2}
        axis_idx = axis_map[self.axis]
        is_neg = self.sign == 'NEG'

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            mirror_mod = obj.modifiers.new(name="Mirror", type='MIRROR')
            # Immediately enable the pressed axis and sign
            mirror_mod.use_axis[axis_idx] = True
            mirror_mod.use_bisect_flip_axis[axis_idx] = is_neg
            # Always enable use_bisect_axis when use_axis is enabled
            if hasattr(mirror_mod, 'use_bisect_axis'):
                mirror_mod.use_bisect_axis[axis_idx] = True
            # Toggle logic
            if not mirror_mod.use_axis[axis_idx]:
                # If axis is off, turn it on and set bisect
                mirror_mod.use_axis[axis_idx] = True
                mirror_mod.use_bisect_flip_axis[axis_idx] = is_neg
                if hasattr(mirror_mod, 'use_bisect_axis'):
                    mirror_mod.use_bisect_axis[axis_idx] = True
            else:
                # If axis is on, toggle bisect or turn off
                if is_neg:
                    if mirror_mod.use_bisect_flip_axis[axis_idx]:
                        # If already negative, turn off axis
                        mirror_mod.use_axis[axis_idx] = False
                        mirror_mod.use_bisect_flip_axis[axis_idx] = False
                    else:
                        # Switch to negative
                        mirror_mod.use_bisect_flip_axis[axis_idx] = True
                else:
                    if not mirror_mod.use_bisect_flip_axis[axis_idx]:
                        # If already positive, turn off axis
                        mirror_mod.use_axis[axis_idx] = False
                    else:
                        # Switch to positive
                        mirror_mod.use_bisect_flip_axis[axis_idx] = False
        return {'FINISHED'}


classes = (
    ROTOR_OT_SetMirrorAxis,
    ROTOR_OT_AddMirrorAxis,
)
