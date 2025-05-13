import bpy
from pathlib import Path
from ..utils import addon


types = [('MIRROR', 'Mirror', 'Mirror Modifier'),
         ('SYMMETRY','Symmetry', 'Mirror using Symmetry operation')]


origines = [('MEDIAN', 'Median Point', 'Mirror Across Median Point of Selected Objects'),
            ('ACTIVE', 'Active Element', 'Mirror Across Active Element'),
            ('CURSOR', 'Cursor', 'Mirror Across 3D Cursor')]



class ROTOR_MT_Mirror(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = 'rotor.mirror_tool'
    bl_label = 'Rotor'
    bl_description = 'Tool for mirroring geometry'
    bl_icon = (Path(__file__).parent.parent / "icons" / "mirror").as_posix()


    def draw_settings(context, layout, tool):
        rotor = addon.pref().tools.rotor
        layout.label(text="Mirror:")
        row = layout.row(align=True)

        label = "None  "
        _type = rotor.mode
        match _type:
            case 'MIRROR': label = "Mirror"
            case 'SYMMETRY': label = "Symmetry"
        row.popover('ROTOR_PT_Type', text=label)


class ROTOR_PT_Type(bpy.types.Panel):
    bl_label = "Type"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_description = ""
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.rotor
        layout.prop(rotor, 'type')


class ROTOR_PT_Origin(bpy.types.Panel):
    bl_label = "Type"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_description = ""
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.rotor
        layout.prop(rotor, 'origin')


class Mirror(bpy.types.PropertyGroup):
    type: bpy.props.EnumProperty(
        name="Type",
        description="Type of the operation",
        items=types,
        default='VISIBLE')

    origin: bpy.props.EnumProperty(
        name="Origin",
        description="Origin of the operation",
        items=origines, 
        default='VISIBLE')


classes = [
    ROTOR_PT_Type,
    ROTOR_PT_Origin,
]