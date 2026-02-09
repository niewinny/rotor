import bpy

snap_items = [
    ("VIEW", "View", "Snap to view plane", "GRID", 1),
    ("ORIGIN", "Origin", "Snap to object origins", "OBJECT_ORIGIN", 2),
    ("FACE", "Face", "Snap to faces", "SNAP_FACE", 3),
    ("VERTEX", "Vertex", "Snap to vertices", "SNAP_VERTEX", 4),
    ("EDGE", "Edge", "Snap to edges", "SNAP_EDGE", 5),
    ("EDGE_CENTER", "Edge Center", "Snap to edge centers", "SNAP_MIDPOINT", 6),
    ("FACE_CENTER", "Face Center", "Snap to face centers", "SNAP_FACE_CENTER", 7),
]


class Duplicate(bpy.types.PropertyGroup):
    axis_x: bpy.props.BoolProperty(
        name="X",
        description="Constrain duplication to X axis",
        default=True,
    )
    axis_y: bpy.props.BoolProperty(
        name="Y",
        description="Constrain duplication to Y axis",
        default=True,
    )
    axis_z: bpy.props.BoolProperty(
        name="Z",
        description="Constrain duplication to Z axis",
        default=True,
    )
    snap: bpy.props.EnumProperty(
        name="Snap",
        description="Snap target for duplicate placement",
        items=snap_items,
        default="VIEW",
    )


classes = (Duplicate,)
