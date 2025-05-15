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

            # Find existing mirror modifier, or create one
            mirror_mod = next((m for m in reversed(obj.modifiers) if m.type == 'MIRROR'), None)
            if mirror_mod is None:
                mirror_mod = obj.modifiers.new(name="Mirror", type='MIRROR')
                mirror_mod.use_axis = [False, False, False]

            # Set up axis and bisect options
            use_axis = mirror_mod.use_axis
            use_bisect_flip = mirror_mod.use_bisect_flip_axis
            use_bisect = getattr(mirror_mod, 'use_bisect_axis', None)

            if not use_axis[axis_idx]:
                use_axis[axis_idx] = True
                use_bisect_flip[axis_idx] = is_neg
                if use_bisect is not None:
                    use_bisect[axis_idx] = True
            else:
                if is_neg:
                    if use_bisect_flip[axis_idx]:
                        use_axis[axis_idx] = False
                        use_bisect_flip[axis_idx] = False
                    else:
                        use_bisect_flip[axis_idx] = True
                else:
                    if not use_bisect_flip[axis_idx]:
                        use_axis[axis_idx] = False
                    else:
                        use_bisect_flip[axis_idx] = False

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

            if obj.modifiers and obj.modifiers[-1].type == 'MIRROR':
                continue

            mirror_mod = obj.modifiers.new(name="Mirror", type='MIRROR')
            mirror_mod.use_axis = [False, False, False]

            mirror_mod.use_axis[axis_idx] = True
            mirror_mod.use_bisect_flip_axis[axis_idx] = is_neg

            if hasattr(mirror_mod, 'use_bisect_axis'):
                mirror_mod.use_bisect_axis[axis_idx] = True

        return {'FINISHED'}


classes = (
    ROTOR_OT_SetMirrorAxis,
    ROTOR_OT_AddMirrorAxis,
)
