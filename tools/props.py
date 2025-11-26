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
]


orientations = [
    ("GLOBAL", "Global", "Mirror using Global orientation", "ORIENTATION_GLOBAL", 1),
    ("LOCAL", "Local", "Mirror using Local orientation", "ORIENTATION_LOCAL", 2),
    ("CURSOR", "Cursor", "Mirror using 3D Cursor orientation", "ORIENTATION_CURSOR", 3),
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

    gizmo_size: bpy.props.FloatProperty(
        name="Gizmo Size",
        description="Size of the mirror gizmo handles",
        default=1.0,
        min=0.1,
        max=5.0,
        soft_min=0.5,
        soft_max=2.0,
    )

    # === Reverse Controls ===
    reverse_controls: bpy.props.BoolProperty(
        name="Reverse Controls",
        description="Reverse axis directions (X becomes -X, -X becomes X, etc.)",
        default=False,
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


classes = (Mirror,)
