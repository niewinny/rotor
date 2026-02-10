import bpy

pivot_items = [
    ("ORIGIN", "Origin", "Snap to object origins", "OBJECT_ORIGIN", 1),
    ("FACE", "Face", "Snap to faces", "SNAP_FACE", 2),
    ("VERTEX", "Vertex", "Snap to vertices", "SNAP_VERTEX", 3),
    ("EDGE", "Edge", "Snap to edges", "SNAP_EDGE", 4),
    ("EDGE_CENTER", "Edge Center", "Snap to edge centers", "SNAP_MIDPOINT", 5),
    ("FACE_CENTER", "Face Center", "Snap to face centers", "SNAP_FACE_CENTER", 6),
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
        default="ORIGIN",
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
    reflect: bpy.props.BoolProperty(
        name="Full",
        description="Double axis projection distance",
        default=False,
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
