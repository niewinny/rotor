import bpy
from pathlib import Path


class ROTOR_MT_Mirror(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = 'rotor.mirror_tool'
    bl_label = 'Rotot'
    bl_description = 'Tool for mirroring geometry'
    bl_icon = (Path(__file__).parent.parent / "icons" / "rotor").as_posix()


    def draw_settings(context, layout, tool):
        pass
