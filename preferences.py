import bpy
from . import btypes
from . import __package__ as base_package


LINKS = [
    ("Support Development", "https://superhivemarket.com/creators/ezelar", "FUND"),
    ("Report Issues", "https://github.com/niewinny/rotor", "URL"),
    ("Documentation", "https://rotor.ezelar.com", "HELP"),
    ("Twitter", "https://twitter.com/_arutkowski", "X"),
]


class ROTOR_OT_OpenURL(bpy.types.Operator):
    bl_idname = "rotor.open_url"
    bl_label = "Open URL"
    bl_description = "Open URL in browser"

    url: bpy.props.StringProperty()

    def execute(self, context):
        import webbrowser
        webbrowser.open(self.url)
        return {"FINISHED"}


class Rotor_Preference(bpy.types.AddonPreferences):
    bl_idname = base_package

    settings: bpy.props.EnumProperty(
        name="Settings",
        description="Settings to display",
        items=[
            ("INFO", "Info", ""),
            ("OPTIONS", "Options", ""),
            ("THEME", "Theme", ""),
        ],
        default="INFO",
    )

    theme: bpy.props.PointerProperty(type=btypes.Theme)
    tools: bpy.props.PointerProperty(type=btypes.Tools)

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)
        split = column.split(factor=0.2)
        col = split.column(align=True)
        col.prop(self, "settings", expand=True)
        col = split.column(align=True)
        col.use_property_split = True

        if self.settings == "INFO":
            self.draw_info(col)

        elif self.settings == "OPTIONS":
            col = col.column(align=True)
            mirror = self.tools.mirror
            col.prop(mirror, "gizmo_size")
            col.prop(mirror, "reverse_controls")

        elif self.settings == "THEME":
            flow = col.grid_flow(
                row_major=False,
                columns=0,
                even_columns=True,
                even_rows=False,
                align=False,
            )
            theme = context.preferences.addons[base_package].preferences.theme

            # Display axis colors
            axis_box = flow.box()
            axis_box.label(text="Axis Colors", icon="ORIENTATION_GLOBAL")
            axis_col = axis_box.column(align=True)
            axis_col.prop(theme.axis, "x")
            axis_col.prop(theme.axis, "y")
            axis_col.prop(theme.axis, "z")
            axis_col.separator()
            axis_col.prop(theme.axis, "g")
            axis_col.prop(theme.axis, "n")

    def draw_info(self, layout):
        box = layout.box()
        col = box.column(align=True)

        row = col.row()
        row.alignment = "CENTER"
        row.scale_y = 2.0
        row.label(text="ROTOR")

        col.separator()
        for label, url, icon in LINKS:
            op = col.operator("rotor.open_url", text=label, icon=icon)
            op.url = url

    def theme_layout(self, layout, theme):
        """Draw a theme layout"""
        for prop in theme.bl_rna.properties:
            if prop.identifier == "name" or prop.identifier == "rna_type":
                continue

            layout.prop(theme, prop.identifier)
        layout.separator()


classes = (ROTOR_OT_OpenURL, Rotor_Preference)
