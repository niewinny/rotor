import bpy
from pathlib import Path
from ..utils import addon


modes = [('MIRROR', 'Mirror', 'Mirror Modifier'),
         ('SYMMETRY','Symmetry', 'Mirror using Symmetry operation')]


elements = [('OBJECT', 'Objects', 'Mirror Objects ', 'OBJECT_DATAMODE', 1),
            ('COLLECTION', 'Collections', 'Mirror Collections', 'OUTLINER_COLLECTION', 2)]


pivots = [('ACTIVE', 'Active Element', 'Mirror Across Active Element', 'PIVOT_ACTIVE', 1),
          ('INDIVIDUAL', 'Individual Elements', 'Mirror Across Individual Elements', 'PIVOT_INDIVIDUAL', 2),
          ('WORLD', 'World Center', 'Mirror Across World Center', 'WORLD', 3),
          ('CUSTOM', 'Custom', 'Mirror Across Custom Point', 'RECORD_OFF', 4)]


orientations = [('GLOBAL', 'Global', 'Mirror using Global orientation', 'ORIENTATION_GLOBAL', 1),
                ('LOCAL', 'Local', 'Mirror using Local orientation', 'ORIENTATION_LOCAL', 2),
                ('CUSTOM', 'Custom', 'Mirror using Custom orientation', 'RECORD_OFF', 3)]



class ROTOR_MT_Mirror(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = 'rotor.mirror_tool'
    bl_label = 'Rotor'
    bl_description = 'Tool for mirroring geometry'
    bl_widget = 'ROTOR_GGT_MirrorGizmoGroup'
    bl_icon = (Path(__file__).parent.parent / "icons" / "mirror").as_posix()


    def draw_settings(context, layout, tool):
        rotor = addon.pref().tools.mirror
        row = layout.row(align=True)

        row.label(text="Mirror:")
        label = "None"
        _type = rotor.element
        match _type:
            case 'OBJECT': label, icon = ("Objects",  'OBJECT_DATAMODE')
            case 'COLLECTION': label, icon = ("Collections",  'OUTLINER_COLLECTION')
        row.popover('ROTOR_PT_Element', text=label, icon=icon)
        row.separator()

        if rotor.element == 'OBJECT':
            row.prop(rotor, 'bisect', text="Bisect", toggle=True)

        row.separator_spacer()

        label = "None"
        match _type:
            case 'GLOBAL': label, icon = ('Global', 'ORIENTATION_GLOBAL')
            case 'LOCAL': label, icon = ('Local', 'ORIENTATION_LOCAL')
            case 'CUSTOM': label, icon = ('Custom', 'RECORD_OFF')
        row.popover('ROTOR_PT_Orientation', text=label, icon=icon)

        label = "None"
        _type = rotor.pivot
        match _type:
            case 'ACTIVE': label, icon = ('Active Element', 'PIVOT_ACTIVE')
            case 'INDIVIDUAL': label, icon = ('Individual Elements', 'PIVOT_INDIVIDUAL')
            case 'WORLD': label, icon = ('World', 'WORLD')
            case 'CUSTOM': label, icon = ('Custom', 'RECORD_OFF')
        row.popover('ROTOR_PT_Pivot', text='', icon=icon)
        row.separator()


class ROTOR_PT_Element(bpy.types.Panel):
    bl_label = "Element"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_description = ""
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.mirror

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, 'element', expand=True)


class ROTOR_PT_Type(bpy.types.Panel):
    bl_label = "Type"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_description = ""
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.mirror

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, 'mode', expand=True)


class ROTOR_PT_Pivot(bpy.types.Panel):
    bl_label = "Type"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_description = ""
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.mirror

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, 'pivot', expand=True)


class ROTOR_PT_Orientation(bpy.types.Panel):
    bl_label = "Type"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_description = ""
    bl_context = 'objectmode'

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.mirror

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, 'orientation', expand=True)


class Mirror(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Type",
        description="Type of the operation",
        items=modes,
        default='MIRROR')

    pivot: bpy.props.EnumProperty(
        name="Pivot",
        description="Pivot of the operation",
        items=pivots, 
        default='ACTIVE')

    element: bpy.props.EnumProperty(
        name="Element",
        description="Element to mirror",
        items=elements,
        default='OBJECT')

    orientation: bpy.props.EnumProperty(
        name="Orientation",
        description="Orientation of the operation",
        items=orientations,
        default='LOCAL')

    bisect: bpy.props.BoolProperty(
        name="Bisect",
        description="Bisect the object using specified axis",
        default=False)

types_classes = (
    Mirror,
)

classes = (
    ROTOR_PT_Element,
    ROTOR_PT_Type,
    ROTOR_PT_Pivot,
    ROTOR_PT_Orientation
)
