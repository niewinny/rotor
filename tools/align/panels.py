import bpy

from ...utils import addon


class ROTOR_PT_AlignSource(bpy.types.Panel):
    bl_label = "Source"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_description = ""
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.align

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, "source", expand=True)


class ROTOR_PT_AlignTargetSource(bpy.types.Panel):
    bl_label = "Target Source"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_description = ""
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.align

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, "target_source", expand=True)


class ROTOR_PT_AlignOrientation(bpy.types.Panel):
    bl_label = "Orientation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_description = ""
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.align

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, "orientation", expand=True)


classes = (
    ROTOR_PT_AlignSource,
    ROTOR_PT_AlignTargetSource,
    ROTOR_PT_AlignOrientation,
)
