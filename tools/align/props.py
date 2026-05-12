import bpy


sources = [
    ("ORIGIN", "Origin", "Use object origin as alignment source", "OBJECT_ORIGIN", 1),
    ("BBOX", "Bounding Box", "Use bounding box face as alignment source", "PIVOT_BOUNDBOX", 2),
]


orientations = [
    ("GLOBAL", "Global", "Align using global axes", "ORIENTATION_GLOBAL", 1),
    ("LOCAL", "Local", "Align using active object's local axes", "ORIENTATION_LOCAL", 2),
]


class Align(bpy.types.PropertyGroup):
    orientation: bpy.props.EnumProperty(
        name="Orientation",
        description="Axis orientation for alignment",
        items=orientations,
        default="GLOBAL",
    )

    source: bpy.props.EnumProperty(
        name="Source",
        description="Snap point on each selected object used for alignment",
        items=sources,
        default="ORIGIN",
    )

    target_source: bpy.props.EnumProperty(
        name="Target Source",
        description="Snap point on the active object when Active is the target",
        items=sources,
        default="ORIGIN",
    )

    target_world: bpy.props.BoolProperty(
        name="World",
        description="Show gizmos for aligning to world origin",
        default=True,
    )

    target_active: bpy.props.BoolProperty(
        name="Active",
        description="Show gizmos for aligning to active object",
        default=True,
    )

    target_cursor: bpy.props.BoolProperty(
        name="Cursor",
        description="Show gizmos for aligning to the 3D cursor",
        default=False,
    )

    tool_fallback: bpy.props.BoolProperty(
        name="Tool Fallback",
        description="Return to previous tool after align operation",
        default=True,
    )


classes = (Align,)
