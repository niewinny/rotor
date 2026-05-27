import bpy

modes = [
    ("MIRROR", "Mirror", "Mirror Modifier"),
    ("SYMMETRY", "Symmetry", "Mirror using Symmetry operation"),
]


elements = [
    ("OBJECT", "Objects", "Mirror Objects ", "OBJECT_DATAMODE", 1),
    ("COLLECTION", "Collections", "Mirror Collections", "OUTLINER_COLLECTION", 2),
]


pivots = [
    ("ACTIVE", "Active Element", "Mirror Across Active Element", "PIVOT_ACTIVE", 1),
    (
        "INDIVIDUAL",
        "Individual Elements",
        "Mirror Across Individual Elements",
        "PIVOT_INDIVIDUAL",
        2,
    ),
    ("WORLD", "World Center", "Mirror Across World Center", "WORLD", 3),
    ("CURSOR", "Cursor", "Mirror Across 3D Cursor", "CURSOR", 4),
    ("CUSTOM", "Custom", "Mirror across a custom point", "OBJECT_ORIGIN", 5),
]


orientations = [
    ("GLOBAL", "Global", "Mirror using Global orientation", "ORIENTATION_GLOBAL", 1),
    ("LOCAL", "Local", "Mirror using Local orientation", "ORIENTATION_LOCAL", 2),
    ("CURSOR", "Cursor", "Mirror using 3D Cursor orientation", "ORIENTATION_CURSOR", 3),
    ("CUSTOM", "Custom", "Mirror using a custom orientation", "OBJECT_ORIGIN", 4),
]


# Edit-mode (mesh) orientations and pivots
mesh_orientations = [
    ("GLOBAL", "Global", "Mirror using Global orientation", "ORIENTATION_GLOBAL", 1),
    ("LOCAL", "Local", "Mirror using Local orientation", "ORIENTATION_LOCAL", 2),
    ("CURSOR", "Cursor", "Mirror using 3D Cursor orientation", "ORIENTATION_CURSOR", 3),
    (
        "NORMAL",
        "Normal",
        "Mirror using the selection Normal orientation",
        "ORIENTATION_NORMAL",
        4,
    ),
    ("CUSTOM", "Custom", "Mirror using a custom orientation", "OBJECT_ORIGIN", 5),
]


mesh_pivots = [
    ("ACTIVE", "Active Element", "Mirror across the active element", "PIVOT_ACTIVE", 1),
    ("MEDIAN", "Median Point", "Mirror across the selection median", "PIVOT_MEDIAN", 2),
    ("ORIGIN", "Object Origin", "Mirror across the object origin", "OBJECT_ORIGIN", 3),
    ("CURSOR", "3D Cursor", "Mirror across the 3D cursor", "PIVOT_CURSOR", 4),
    ("CUSTOM", "Custom", "Mirror across a custom point", "OBJECT_ORIGIN", 5),
]


class Mirror(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Type", description="Type of the operation", items=modes, default="MIRROR"
    )

    pivot: bpy.props.EnumProperty(
        name="Pivot",
        description="Pivot of the operation",
        items=pivots,
        default="ACTIVE",
    )

    element: bpy.props.EnumProperty(
        name="Element",
        description="Element to mirror",
        items=elements,
        default="OBJECT",
    )

    orientation: bpy.props.EnumProperty(
        name="Orientation",
        description="Orientation of the operation",
        items=orientations,
        default="LOCAL",
    )

    # Custom plane (world space): location = custom pivot, rotation = custom orientation
    custom_location: bpy.props.FloatVectorProperty(
        name="Custom Location",
        description="Custom pivot point (world space)",
        size=3,
        subtype="XYZ",
        default=(0.0, 0.0, 0.0),
    )

    custom_rotation: bpy.props.FloatVectorProperty(
        name="Custom Rotation",
        description="Custom orientation (world space)",
        size=3,
        subtype="EULER",
        default=(0.0, 0.0, 0.0),
    )

    real: bpy.props.BoolProperty(
        name="Real",
        description="Create real duplicated objects instead of mirror modifiers",
        default=False,
    )

    bisect: bpy.props.BoolProperty(
        name="Bisect",
        description="Bisect the object using specified axis",
        default=False,
    )

    tool_fallback: bpy.props.BoolProperty(
        name="Tool Fallback",
        description="Return to previous tool after mirror operation",
        default=True,
    )

    # === Reverse Controls ===
    reverse_controls: bpy.props.BoolProperty(
        name="Reverse Controls",
        description="Reverse axis directions (X becomes -X, -X becomes X, etc.)",
        default=False,
    )

    # === Include Active ===
    include_active: bpy.props.BoolProperty(
        name="Include Active",
        description="Include active object in the mirror operation when using Active pivot",
        default=True,
    )

    # === Empty Display Settings ===
    empty_display_type: bpy.props.EnumProperty(
        name="Empty Display",
        description="Display type for created empty objects",
        items=[
            ("PLAIN_AXES", "Plain Axes", ""),
            ("ARROWS", "Arrows", ""),
            ("SINGLE_ARROW", "Single Arrow", ""),
            ("CIRCLE", "Circle", ""),
            ("CUBE", "Cube", ""),
            ("SPHERE", "Sphere", ""),
            ("CONE", "Cone", ""),
        ],
        default="PLAIN_AXES",
    )

    empty_display_size: bpy.props.FloatProperty(
        name="Empty Size",
        description="Size of created empty objects",
        default=1.0,
        min=0.01,
        max=100.0,
        soft_min=0.1,
        soft_max=10.0,
    )

    # === Mirror Modifier Properties with Enable Checkboxes ===
    # Clipping & Merge
    apply_use_clip: bpy.props.BoolProperty(
        name="Apply",
        description="Apply clipping setting to new modifiers",
        default=False,
    )
    use_clip: bpy.props.BoolProperty(
        name="Clipping",
        description="Prevent vertices from passing through the mirror plane",
        default=False,
    )

    apply_use_mirror_merge: bpy.props.BoolProperty(
        name="Apply",
        description="Apply merge setting to new modifiers",
        default=False,
    )
    use_mirror_merge: bpy.props.BoolProperty(
        name="Merge",
        description="Merge vertices at the center",
        default=True,
    )

    apply_merge_threshold: bpy.props.BoolProperty(
        name="Apply",
        description="Apply merge threshold to new modifiers",
        default=False,
    )
    merge_threshold: bpy.props.FloatProperty(
        name="Merge Threshold",
        description="Distance within which mirrored vertices are merged",
        default=0.001,
        min=0.0,
        soft_max=1.0,
        precision=4,
        unit="LENGTH",
    )

    apply_bisect_threshold: bpy.props.BoolProperty(
        name="Apply",
        description="Apply bisect threshold to new modifiers",
        default=False,
    )
    bisect_threshold: bpy.props.FloatProperty(
        name="Bisect Threshold",
        description="Threshold for bisecting geometry",
        default=0.001,
        min=0.0,
        soft_max=1.0,
        precision=4,
        unit="LENGTH",
    )

    # UV Settings
    apply_use_mirror_u: bpy.props.BoolProperty(
        name="Apply",
        description="Apply mirror U setting to new modifiers",
        default=False,
    )
    use_mirror_u: bpy.props.BoolProperty(
        name="Flip U",
        description="Mirror U texture coordinates",
        default=False,
    )

    apply_use_mirror_v: bpy.props.BoolProperty(
        name="Apply",
        description="Apply mirror V setting to new modifiers",
        default=False,
    )
    use_mirror_v: bpy.props.BoolProperty(
        name="Flip V",
        description="Mirror V texture coordinates",
        default=False,
    )

    apply_mirror_offset_u: bpy.props.BoolProperty(
        name="Apply",
        description="Apply mirror offset U to new modifiers",
        default=False,
    )
    mirror_offset_u: bpy.props.FloatProperty(
        name="Flip U Offset",
        description="Amount to offset mirrored UVs on flip",
        default=0.0,
        soft_min=-1.0,
        soft_max=1.0,
    )

    apply_mirror_offset_v: bpy.props.BoolProperty(
        name="Apply",
        description="Apply mirror offset V to new modifiers",
        default=False,
    )
    mirror_offset_v: bpy.props.FloatProperty(
        name="Flip V Offset",
        description="Amount to offset mirrored UVs on flip",
        default=0.0,
        soft_min=-1.0,
        soft_max=1.0,
    )

    apply_offset_u: bpy.props.BoolProperty(
        name="Apply",
        description="Apply offset U to new modifiers",
        default=False,
    )
    offset_u: bpy.props.FloatProperty(
        name="Offset U",
        description="Offset U texture coordinates",
        default=0.0,
        soft_min=-1.0,
        soft_max=1.0,
    )

    apply_offset_v: bpy.props.BoolProperty(
        name="Apply",
        description="Apply offset V to new modifiers",
        default=False,
    )
    offset_v: bpy.props.FloatProperty(
        name="Offset V",
        description="Offset V texture coordinates",
        default=0.0,
        soft_min=-1.0,
        soft_max=1.0,
    )

    # Other Settings
    apply_use_mirror_vertex_groups: bpy.props.BoolProperty(
        name="Apply",
        description="Apply mirror vertex groups setting to new modifiers",
        default=False,
    )
    use_mirror_vertex_groups: bpy.props.BoolProperty(
        name="Vertex Groups",
        description="Mirror vertex groups (e.g., .L to .R)",
        default=False,
    )

    apply_use_mirror_udim: bpy.props.BoolProperty(
        name="Apply",
        description="Apply mirror UDIM setting to new modifiers",
        default=False,
    )
    use_mirror_udim: bpy.props.BoolProperty(
        name="UDIM",
        description="Mirror UDIMs",
        default=False,
    )


class MirrorMesh(bpy.types.PropertyGroup):
    orientation: bpy.props.EnumProperty(
        name="Orientation",
        description="Orientation of the mirror plane",
        items=mesh_orientations,
        default="NORMAL",
    )

    pivot: bpy.props.EnumProperty(
        name="Pivot",
        description="Location of the mirror plane",
        items=mesh_pivots,
        default="MEDIAN",
    )

    # Custom plane (world space): location = custom pivot, rotation = custom orientation
    custom_location: bpy.props.FloatVectorProperty(
        name="Custom Location",
        description="Custom mirror plane location (world space)",
        size=3,
        subtype="XYZ",
        default=(0.0, 0.0, 0.0),
    )

    custom_rotation: bpy.props.FloatVectorProperty(
        name="Custom Rotation",
        description="Custom mirror plane orientation (world space)",
        size=3,
        subtype="EULER",
        default=(0.0, 0.0, 0.0),
    )

    merge: bpy.props.BoolProperty(
        name="Merge",
        description="Weld the mirrored geometry to the original at the seam",
        default=True,
    )

    merge_threshold: bpy.props.FloatProperty(
        name="Merge Distance",
        description="Distance within which mirrored vertices are merged at the seam",
        default=0.0001,
        min=0.0,
        soft_max=1.0,
        precision=5,
        unit="LENGTH",
    )

    tool_fallback: bpy.props.BoolProperty(
        name="Tool Fallback",
        description="Return to previous tool after the mirror operation",
        default=True,
    )

    reverse_controls: bpy.props.BoolProperty(
        name="Reverse Controls",
        description="Reverse axis directions (X becomes -X, -X becomes X, etc.)",
        default=False,
    )


classes = (Mirror, MirrorMesh)
