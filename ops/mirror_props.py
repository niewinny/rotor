from bpy.props import BoolProperty, StringProperty
from bpy.types import PropertyGroup, UIList


class ROTOR_PG_MirrorObjectItem(PropertyGroup):
    """Property group for object items in mirror operations"""

    name: StringProperty(name="Object Name")
    enabled: BoolProperty(name="Enabled", default=True)
    has_mirror_modifier: BoolProperty(name="Has Mirror Modifier", default=False)


class ROTOR_PG_MirrorCollectionItem(PropertyGroup):
    """Property group for collection items in mirror operations"""

    name: StringProperty(name="Collection Name")
    enabled: BoolProperty(name="Enabled", default=True)


class ROTOR_UL_MirrorObjectList(UIList):
    """UIList for displaying mirror objects"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)

            # Get the operator's is_disabling state
            is_disabling = getattr(data, "is_disabling", False)

            # Check if object has mirror modifier to enable/disable checkbox
            if not item.has_mirror_modifier and is_disabling:
                # Only disable if we're trying to disable and object has no modifier
                row.enabled = False

            row.prop(item, "enabled", text="")

            # Choose icon based on active object and mirror modifier status
            if not item.has_mirror_modifier and is_disabling:
                # Objects without mirror modifiers get an error icon only when disabling
                icon_type = "ERROR"
            elif context.active_object and item.name == context.active_object.name:
                # Active object
                icon_type = "OBJECT_HIDDEN"
            else:
                # Other objects
                icon_type = "OBJECT_DATA"

            # Show object name
            row.label(text=item.name, icon=icon_type)

            # Add tag for new/edit status
            if item.has_mirror_modifier:
                row.label(text="[Edit]")
            elif not is_disabling:
                # Will create new modifier when enabling
                row.label(text="[New]")
            # No tag when disabling and no modifier exists
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon="OBJECT_DATA")


types_classes = (
    ROTOR_PG_MirrorObjectItem,
    ROTOR_PG_MirrorCollectionItem,
)

classes = (ROTOR_UL_MirrorObjectList,)
