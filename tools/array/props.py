import bpy

mode_items = [
    ("LINEAR", "Linear", "Distribute duplicates along the guide", "ARROW_LEFTRIGHT", 1),
    ("CIRCLE", "Circle", "Distribute duplicates in a circle", "MESH_CIRCLE", 2),
]

pivot_items = [
    ("INCREMENT", "Increment", "Snap to grid increments", "SNAP_INCREMENT", 1),
    ("GRID", "Grid", "Snap to absolute grid positions", "SNAP_GRID", 2),
    ("ORIGIN", "Origin", "Snap to object origins", "OBJECT_ORIGIN", 3),
    ("FACE", "Face", "Snap to faces", "SNAP_FACE", 4),
    ("VERTEX", "Vertex", "Snap to vertices", "SNAP_VERTEX", 5),
    ("EDGE", "Edge", "Snap to edges", "SNAP_EDGE", 6),
    ("EDGE_CENTER", "Edge Center", "Snap to edge centers", "SNAP_MIDPOINT", 7),
    ("FACE_CENTER", "Face Center", "Snap to face centers", "SNAP_FACE_CENTER", 8),
]

orientation_items = [
    ("GLOBAL", "Global", "Use global orientation", "ORIENTATION_GLOBAL", 1),
    ("LOCAL", "Local", "Use local orientation", "ORIENTATION_LOCAL", 2),
]


class ArraySnap(bpy.types.PropertyGroup):
    pivot: bpy.props.EnumProperty(
        name="Pivot",
        description="Snap target for array placement",
        items=pivot_items,
        default="INCREMENT",
    )
    orientation: bpy.props.EnumProperty(
        name="Orientation",
        description="Orientation for snap axes",
        items=orientation_items,
        default="GLOBAL",
    )


class Array(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Distribution mode for duplicates",
        items=mode_items,
        default="LINEAR",
    )
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
    double: bpy.props.BoolProperty(
        name="Double",
        description="Double the guide distance",
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
    align: bpy.props.BoolProperty(
        name="Align",
        description="Orient all objects (including selected) to face the cursor",
        default=False,
    )
    face_axis: bpy.props.EnumProperty(
        name="Face",
        description="Direction instances face on the circle (Ctrl+X/Y/Z)",
        items=[
            ("NONE", "None", "Automatic facing direction"),
            ("X", "X", "Face along X axis"),
            ("Y", "Y", "Face along Y axis"),
            ("Z", "Z", "Face along Z axis"),
        ],
        default="NONE",
    )
    real: bpy.props.BoolProperty(
        name="Real",
        description="Create real object copies instead of GN Array modifier",
        default=False,
    )
    snap: bpy.props.PointerProperty(type=ArraySnap)


classes = (ArraySnap, Array)
