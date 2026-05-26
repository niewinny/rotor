import bmesh
from mathutils import Matrix, Vector

from ..utils import addon


def _selection(bm):
    """Return (verts, edges, faces) lists of the current selection."""
    verts = [v for v in bm.verts if v.select]
    edges = [e for e in bm.edges if e.select]
    faces = [f for f in bm.faces if f.select]
    return verts, edges, faces


def _build_normal_frame(bm, mw3, pivot, sel_verts):
    """Build a world-space orientation frame from the selection normal.

    With ``pivot == 'ACTIVE'`` and an active face, the frame follows that face;
    otherwise it uses the averaged normal of the selected faces (falling back to
    the averaged vertex normal for edge/vertex selections).

    Returns a 3x3 matrix whose columns are the X/Y/Z axis directions in world space.
    """
    n_local = Vector((0.0, 0.0, 0.0))
    t_local = None

    active = bm.select_history.active
    if pivot == "ACTIVE" and isinstance(active, bmesh.types.BMFace):
        n_local = active.normal.copy()
        t_local = active.loops[0].edge.verts[1].co - active.loops[0].edge.verts[0].co
    else:
        sel_faces = [f for f in bm.faces if f.select]
        if sel_faces:
            for f in sel_faces:
                n_local += f.normal
            ref = sel_faces[0]
            t_local = ref.loops[0].edge.verts[1].co - ref.loops[0].edge.verts[0].co
        else:
            for v in sel_verts:
                n_local += v.normal

    z = (mw3 @ n_local).normalized()
    if z.length < 1e-6:
        z = Vector((0.0, 0.0, 1.0))

    if t_local is not None:
        t = mw3 @ t_local
    else:
        t = z.orthogonal()

    # Orthonormalize the tangent against the normal
    t = t - z * t.dot(z)
    if t.length < 1e-6:
        t = z.orthogonal()
    x = t.normalized()
    y = z.cross(x).normalized()

    return Matrix((x, y, z)).transposed()


def get_mesh_mirror_frame(context):
    """Compute the world-space mirror plane frame for the edit-mesh object.

    Returns ``(world_pivot, frame)`` where ``world_pivot`` is the plane origin and
    ``frame`` is a 3x3 matrix with the X/Y/Z axis directions as columns, or
    ``None`` when there is no usable selection.
    """
    obj = context.edit_object
    if not obj or obj.type != "MESH":
        return None

    pref = addon.pref().tools.mesh
    bm = bmesh.from_edit_mesh(obj.data)

    sel_verts = [v for v in bm.verts if v.select]

    # A selection is only required to derive the location from the elements
    # (Active/Median) or to derive the Normal orientation.
    needs_selection = pref.pivot in {"ACTIVE", "MEDIAN"} or pref.orientation == "NORMAL"
    if needs_selection and not sel_verts:
        return None

    mw = obj.matrix_world
    mw3 = mw.to_3x3()

    # Pivot location (world space)
    if pref.pivot == "ORIGIN":
        world_pivot = mw.translation.copy()
    elif pref.pivot == "CURSOR":
        world_pivot = context.scene.cursor.location.copy()
    elif pref.pivot == "ACTIVE":
        active = bm.select_history.active
        if isinstance(active, bmesh.types.BMFace):
            co_local = active.calc_center_median()
        elif isinstance(active, bmesh.types.BMVert):
            co_local = active.co.copy()
        elif isinstance(active, bmesh.types.BMEdge):
            co_local = (active.verts[0].co + active.verts[1].co) / 2.0
        else:
            co_local = sum((v.co for v in sel_verts), Vector()) / len(sel_verts)
        world_pivot = mw @ co_local
    else:  # MEDIAN
        co_local = sum((v.co for v in sel_verts), Vector()) / len(sel_verts)
        world_pivot = mw @ co_local

    # Orientation frame (world space)
    orientation = pref.orientation
    if orientation == "GLOBAL":
        frame = Matrix.Identity(3)
    elif orientation == "LOCAL":
        frame = mw3.normalized()
    elif orientation == "CURSOR":
        frame = context.scene.cursor.matrix.to_3x3().normalized()
    else:  # NORMAL
        frame = _build_normal_frame(bm, mw3, pref.pivot, sel_verts)

    return world_pivot, frame


def symmetrize_geom(bm, verts, edges, faces, plane_co, plane_no, merge, dist, select_result=False):
    """Symmetrize geometry across an arbitrary plane.

    Clears the side opposite to ``plane_no``, duplicates the kept side, reflects
    it across the plane and (optionally) welds the seam. Mirrors the behavior of
    the object-mode real mirror, but applied destructively to mesh geometry.

    Returns the number of mirrored vertices created.
    """
    geom = list(verts) + list(edges) + list(faces)
    if not geom:
        return 0

    n = plane_no.normalized()
    tol = max(dist, 1e-5)

    def on_plane(v):
        return abs((v.co - plane_co).dot(n)) <= tol

    # 1. Bisect, clearing the side opposite to the plane normal.
    res = bmesh.ops.bisect_plane(
        bm,
        geom=geom,
        dist=tol,
        plane_co=plane_co,
        plane_no=n,
        clear_inner=True,
        clear_outer=False,
    )
    kept = [g for g in res["geom"] if g.is_valid]

    # 2. Remove faces that lie flat on the plane (e.g. the face that defines the
    #    mirror), so they don't remain as a wall between the two halves.
    on_plane_faces = [
        f
        for f in kept
        if isinstance(f, bmesh.types.BMFace) and all(on_plane(v) for v in f.verts)
    ]
    if on_plane_faces:
        bmesh.ops.delete(bm, geom=on_plane_faces, context="FACES_ONLY")
        kept = [g for g in kept if g.is_valid]

    if not kept:
        return 0

    # 3. Duplicate the kept side.
    dup = bmesh.ops.duplicate(bm, geom=kept)
    vmap = dup["vert_map"]
    dup_verts = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]
    dup_faces = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]

    # 4. Reflect the duplicate across the plane.
    for v in dup_verts:
        d = (v.co - plane_co).dot(n)
        v.co = v.co - 2.0 * d * n

    # 5. Negative scale flips winding — restore it.
    if dup_faces:
        bmesh.ops.reverse_faces(bm, faces=dup_faces)

    # 6. Weld the seam: verts on the plane coincide with their reflected copies.
    if merge:
        seam = []
        for v in kept:
            if not (isinstance(v, bmesh.types.BMVert) and v.is_valid and on_plane(v)):
                continue
            seam.append(v)
            mv = vmap.get(v)
            if mv is not None and mv.is_valid:
                seam.append(mv)
        if seam:
            bmesh.ops.remove_doubles(bm, verts=seam, dist=tol)

    if select_result:
        for v in dup_verts:
            if v.is_valid:
                v.select_set(True)

    return len(dup_verts)
