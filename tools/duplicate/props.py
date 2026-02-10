import bpy

pivot_items = [
    ("VIEW", "View", "Snap to view plane", "GRID", 1),
    ("ORIGIN", "Origin", "Snap to object origins", "OBJECT_ORIGIN", 2),
    ("FACE", "Face", "Snap to faces", "SNAP_FACE", 3),
    ("VERTEX", "Vertex", "Snap to vertices", "SNAP_VERTEX", 4),
    ("EDGE", "Edge", "Snap to edges", "SNAP_EDGE", 5),
    ("EDGE_CENTER", "Edge Center", "Snap to edge centers", "SNAP_MIDPOINT", 6),
    ("FACE_CENTER", "Face Center", "Snap to face centers", "SNAP_FACE_CENTER", 7),
]

orientation_items = [
    ("GLOBAL", "Global", "Use global orientation", "ORIENTATION_GLOBAL", 1),
    ("LOCAL", "Local", "Use local orientation", "ORIENTATION_LOCAL", 2),
]


class DuplicateSnap(bpy.types.PropertyGroup):
    pivot: bpy.props.EnumProperty(
        name="Pivot",
        description="Snap target for duplicate placement",
        items=pivot_items,
        default="VIEW",
    )
    orientation: bpy.props.EnumProperty(
        name="Orientation",
        description="Orientation for snap axes",
        items=orientation_items,
        default="GLOBAL",
    )


class Duplicate(bpy.types.PropertyGroup):
    axis_x: bpy.props.BoolProperty(
        name="X",
        description="Constrain duplication to X axis",
        default=False,
    )
    axis_y: bpy.props.BoolProperty(
        name="Y",
        description="Constrain duplication to Y axis",
        default=False,
    )
    axis_z: bpy.props.BoolProperty(
        name="Z",
        description="Constrain duplication to Z axis",
        default=False,
    )
    count: bpy.props.IntProperty(
        name="Count",
        description="Number of duplicates along the guide",
        default=1,
        min=1,
    )
    scale: bpy.props.FloatProperty(
        name="Scale",
        description="Scale factor for duplicates (interpolated along guide)",
        default=1.0,
        min=0.01,
        soft_min=0.1,
        soft_max=10.0,
    )
    snap: bpy.props.PointerProperty(type=DuplicateSnap)


classes = (DuplicateSnap, Duplicate)
