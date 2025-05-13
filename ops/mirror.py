import bpy

class ROTOR_OT_MirrorAxis(bpy.types.Operator):
    bl_idname = "rotor.mirror_axis"
    bl_label = "Rotor Mirror Axis"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print('now')
        return {'FINISHED'}


classes = (
    ROTOR_OT_MirrorAxis,
)
