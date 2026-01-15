import bpy
from ..utils import addon


class ROTOR_PT_Element(bpy.types.Panel):
    bl_label = "Element"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_description = ""
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.mirror

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, "element", expand=True)


class ROTOR_PT_Type(bpy.types.Panel):
    bl_label = "Type"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_description = ""
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.mirror

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, "mode", expand=True)


class ROTOR_PT_Pivot(bpy.types.Panel):
    bl_label = "Type"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_description = ""
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.mirror

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, "pivot", expand=True)


class ROTOR_PT_Orientation(bpy.types.Panel):
    bl_label = "Type"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_description = ""
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.mirror

        layout.use_property_split = False
        col = layout.column(align=True)
        col.scale_y = 1.6
        col.prop(rotor, "orientation", expand=True)


class ROTOR_PT_ToolOptions(bpy.types.Panel):
    bl_label = "Tool Options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_description = "Tool options"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.mirror

        layout.use_property_split = True
        col = layout.column(align=True)

        row = col.row(align=True)
        row.active = rotor.pivot == "ACTIVE"
        row.prop(rotor, "include_active")


class ROTOR_PT_MirrorOptions(bpy.types.Panel):
    bl_label = "Mirror Options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_description = "Mirror modifier settings"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        rotor = addon.pref().tools.mirror

        layout.use_property_split = False
        layout.use_property_decorate = False

        # === Clipping & Merge ===
        box = layout.box()
        box.label(text="Clipping & Merge", icon="MOD_MIRROR")
        col = box.column(align=True)

        # use_clip row
        row = col.row(align=True)
        row.prop(rotor, "apply_use_clip", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_use_clip
        sub.prop(rotor, "use_clip")

        # use_mirror_merge row
        row = col.row(align=True)
        row.prop(rotor, "apply_use_mirror_merge", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_use_mirror_merge
        sub.prop(rotor, "use_mirror_merge")

        # merge_threshold row
        row = col.row(align=True)
        row.prop(rotor, "apply_merge_threshold", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_merge_threshold
        sub.prop(rotor, "merge_threshold")

        # bisect_threshold row
        row = col.row(align=True)
        row.prop(rotor, "apply_bisect_threshold", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_bisect_threshold
        sub.prop(rotor, "bisect_threshold")

        # === UV Settings ===
        box = layout.box()
        box.label(text="UV Settings", icon="UV")
        col = box.column(align=True)

        # use_mirror_u row
        row = col.row(align=True)
        row.prop(rotor, "apply_use_mirror_u", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_use_mirror_u
        sub.prop(rotor, "use_mirror_u")

        # use_mirror_v row
        row = col.row(align=True)
        row.prop(rotor, "apply_use_mirror_v", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_use_mirror_v
        sub.prop(rotor, "use_mirror_v")

        # mirror_offset_u row
        row = col.row(align=True)
        row.prop(rotor, "apply_mirror_offset_u", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_mirror_offset_u
        sub.prop(rotor, "mirror_offset_u")

        # mirror_offset_v row
        row = col.row(align=True)
        row.prop(rotor, "apply_mirror_offset_v", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_mirror_offset_v
        sub.prop(rotor, "mirror_offset_v")

        # offset_u row
        row = col.row(align=True)
        row.prop(rotor, "apply_offset_u", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_offset_u
        sub.prop(rotor, "offset_u")

        # offset_v row
        row = col.row(align=True)
        row.prop(rotor, "apply_offset_v", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_offset_v
        sub.prop(rotor, "offset_v")

        # === Other Settings ===
        box = layout.box()
        box.label(text="Other", icon="SETTINGS")
        col = box.column(align=True)

        # use_mirror_vertex_groups row
        row = col.row(align=True)
        row.prop(rotor, "apply_use_mirror_vertex_groups", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_use_mirror_vertex_groups
        sub.prop(rotor, "use_mirror_vertex_groups")

        # use_mirror_udim row
        row = col.row(align=True)
        row.prop(rotor, "apply_use_mirror_udim", text="")
        sub = row.row(align=True)
        sub.enabled = rotor.apply_use_mirror_udim
        sub.prop(rotor, "use_mirror_udim")


classes = (
    ROTOR_PT_Element,
    ROTOR_PT_Type,
    ROTOR_PT_Pivot,
    ROTOR_PT_Orientation,
    ROTOR_PT_ToolOptions,
    ROTOR_PT_MirrorOptions,
)
