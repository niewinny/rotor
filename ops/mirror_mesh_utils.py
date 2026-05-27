import bmesh
from mathutils import Euler, Matrix, Vector

from ..utils import addon


def _selection(bm):
    """Return (verts, edges, faces) lists of the current selection."""
    verts = [v for v in bm.verts if v.select]
    edges = [e for e in bm.edges if e.select]
    faces = [f for f in bm.faces if f.select]
    return verts, edges, faces


# Python port of Blender's "Normal" transform orientation for edit meshes, so
# the Mirror tool's NORMAL frame matches Blender 1:1. Mirrors getTransformOrientation_ex
# + createSpaceNormal/createSpaceNormalTangent (editors/transform/transform_orientations.cc,
# helpers in bmesh_marking.cc / bmesh_polygon.cc).

_EPS = 1e-6


def _project(a, b):
    d = b.dot(b)
    if d < 1e-12:
        return Vector((0.0, 0.0, 0.0))
    return b * (a.dot(b) / d)


def _edge_exists(va, vb):
    for e in va.link_edges:
        if e.other_vert(va) == vb:
            return e
    return None


def _tri_unique_edge_tangent(verts):
    """Tangent along the most 'unique' edge of a triangle."""
    difs = [0.0, 0.0, 0.0]
    for i_prev, i_curr, i_next in ((1, 2, 0), (2, 0, 1), (0, 1, 2)):
        co = verts[i_curr].co
        o0 = verts[i_prev].co
        o1 = verts[i_next].co
        proj_dir = (o0 + o1) * 0.5 - co
        difs[i_next] = (_project(o0, proj_dir) - _project(o1, proj_dir)).length_squared
    index = max(range(3), key=lambda i: difs[i])
    return (verts[index].co - verts[(index + 1) % 3].co).normalized()


def _face_tangent_auto(f):
    n = len(f.verts)
    if n == 3:
        return _tri_unique_edge_tangent([loop.vert for loop in f.loops])
    if n == 4:
        return f.calc_tangent_edge_pair()
    return f.calc_tangent_edge()


def _editselection_center(ele):
    if isinstance(ele, bmesh.types.BMVert):
        return ele.co.copy()
    if isinstance(ele, bmesh.types.BMEdge):
        return (ele.verts[0].co + ele.verts[1].co) * 0.5
    return ele.calc_center_median()


def _editselection_normal(ele):
    if isinstance(ele, bmesh.types.BMVert):
        return ele.normal.copy()
    if isinstance(ele, bmesh.types.BMEdge):
        normal = ele.verts[0].normal + ele.verts[1].normal
        plane = ele.verts[1].co - ele.verts[0].co
        vec = normal.cross(plane)
        normal = plane.cross(vec)
        normal.normalize()
        return normal
    return ele.normal.copy()


def _editselection_plane(ele, history):
    if isinstance(ele, bmesh.types.BMVert):
        prev = history[-2] if len(history) >= 2 and history[-1] == ele else None
        if prev is not None:
            plane = _editselection_center(prev) - ele.co
        else:
            no = ele.normal
            vec = Vector((0.0, 0.0, 0.0))
            if no[0] < 0.5:
                vec[0] = 1.0
            elif no[1] < 0.5:
                vec[1] = 1.0
            else:
                vec[2] = 1.0
            plane = no.cross(vec)
        plane.normalize()
        return plane
    if isinstance(ele, bmesh.types.BMEdge):
        if ele.is_boundary:
            loop = ele.link_loops[0]
            plane = loop.vert.co - loop.link_loop_next.vert.co
        elif ele.verts[1].co[1] > ele.verts[0].co[1]:
            plane = ele.verts[1].co - ele.verts[0].co
        else:
            plane = ele.verts[0].co - ele.verts[1].co
        plane.normalize()
        return plane
    return _face_tangent_auto(ele)


def _create_space_normal(normal):
    z = normal.normalized()
    if z.length < _EPS:
        return None
    x = z.cross(Vector((0.0, 0.0, 1.0)))
    if x.length < _EPS:
        x = Vector((1.0, 0.0, 0.0)).cross(z)
    x.normalize()
    y = z.cross(x).normalized()
    return Matrix((x, y, z)).transposed()


def _create_space_normal_tangent(normal, tangent):
    """Basis with Z = normal, X = cross(Z, plane), Y = cross(Z, X).

    Blender stores -tangent in Y; that negation and the trailing
    negate_v3(r_plane) in getTransformOrientation_ex cancel out.
    """
    z = normal.normalized()
    if z.length < _EPS:
        return None
    y = -tangent
    if y.length < _EPS:
        y = Vector((0.0, 0.0, 1.0))
    x = z.cross(y)
    if x.length < _EPS:
        return None
    x.normalize()
    y = z.cross(x)
    if y.length < _EPS:
        return None
    y.normalize()
    return Matrix((x, y, z)).transposed()


def _build_normal_frame(bm, mw, around_active):
    """World-space NORMAL orientation frame matching Blender's edit-mesh logic.

    ``around_active`` reproduces ``around == V3D_AROUND_ACTIVE`` (i.e. the
    Active Element pivot): the frame then follows the active element instead of
    the aggregate selection. Returns a 3x3 matrix whose columns are the X/Y/Z
    axis directions in world space, or ``None`` when no usable selection.
    """
    history = list(bm.select_history)
    active = history[-1] if history else None

    normal = Vector((0.0, 0.0, 0.0))
    plane = Vector((0.0, 0.0, 0.0))
    result = ""

    if around_active and active is not None:
        normal = _editselection_normal(active)
        plane = _editselection_plane(active, history)
        if isinstance(active, bmesh.types.BMVert):
            result = "VERT"
        elif isinstance(active, bmesh.types.BMEdge):
            result = "EDGE"
        else:
            result = "FACE"
    else:
        sel_verts = [v for v in bm.verts if v.select]
        sel_edges = [e for e in bm.edges if e.select]
        sel_faces = [f for f in bm.faces if f.select]

        if sel_faces:
            for f in sel_faces:
                normal += f.normal
                plane += _face_tangent_auto(f)
            result = "FACE"
        elif len(sel_verts) == 3:
            v_tri = sel_verts
            edge_a = v_tri[0].co - v_tri[1].co
            edge_b = v_tri[1].co - v_tri[2].co
            normal = edge_a.cross(edge_b)
            normal.normalize()
            no_test = v_tri[0].normal + v_tri[1].normal + v_tri[2].normal
            if no_test.dot(normal) < 0.0:
                normal = -normal
            e = None
            e_len = 0.0
            if sel_edges:
                for j in range(3):
                    e_test = _edge_exists(v_tri[j], v_tri[(j + 1) % 3])
                    if e_test is not None and e_test.select:
                        l2 = e_test.calc_length() ** 2
                        if e is None or e_len < l2:
                            e = e_test
                            e_len = l2
            if e is not None:
                if e.is_boundary:
                    loop = e.link_loops[0]
                    plane = loop.vert.co - loop.link_loop_next.vert.co
                else:
                    plane = e.verts[0].co - e.verts[1].co
            else:
                plane = _tri_unique_edge_tangent(v_tri)
            result = "FACE"
        elif len(sel_edges) == 1 or len(sel_verts) == 2:
            eed = sel_edges[0] if len(sel_edges) == 1 else None
            v_pair = list(eed.verts) if eed is not None else list(sel_verts)
            swap = False
            if isinstance(active, bmesh.types.BMVert) and active == v_pair[1]:
                swap = True
            elif eed is not None and eed.is_boundary and eed.link_loops[0].vert != v_pair[0]:
                swap = True
            if swap:
                v_pair[0], v_pair[1] = v_pair[1], v_pair[0]
            normal = v_pair[1].normal + v_pair[0].normal
            plane = v_pair[1].co - v_pair[0].co
            if plane.length > _EPS:
                plane.normalize()
                # Make the normal perpendicular to the edge (local space).
                normal = normal - plane * normal.dot(plane)
                if normal.length < _EPS:
                    normal = plane.orthogonal()
            result = "EDGE"
        elif len(sel_verts) == 1:
            v = sel_verts[0]
            normal = v.normal.copy()
            edges = v.link_edges
            if len(edges) == 2:
                e0, e1 = edges[0], edges[1]
                vp0 = e0.other_vert(v)
                vp1 = e1.other_vert(v)
                swap = False
                if e0.is_boundary:
                    if e0.link_loops[0].vert != v:
                        swap = True
                elif e0.calc_length() ** 2 < e1.calc_length() ** 2:
                    swap = True
                if swap:
                    vp0, vp1 = vp1, vp0
                plane = (v.co - vp0.co).normalized() + (vp1.co - v.co).normalized()
            result = "EDGE" if plane.length > _EPS else "VERT"
        elif len(sel_verts) > 3:
            for v in sel_verts:
                normal += v.normal
            normal.normalize()
            result = "VERT"
        else:
            return None

    # Trailing negate of the plane (matches getTransformOrientation_ex).
    plane = -plane

    # Local -> world. Edges use the plain matrix; everything else uses the
    # inverse-transpose ("normal matrix"), matching Blender exactly.
    mw3 = mw.to_3x3()
    if result == "EDGE":
        normal = mw3 @ normal
        plane = mw3 @ plane
        # Re-project so the normal stays perpendicular to the edge (world space).
        normal = normal - _project(normal, plane)
    else:
        nmat = mw3.inverted_safe().transposed()
        normal = nmat @ normal
        plane = nmat @ plane

    normal.normalize()
    plane.normalize()

    # ORIENTATION_USE_PLANE: EDGE/FACE need a tangent; fall back to VERT if none.
    if result in {"EDGE", "FACE"} and plane.length < _EPS:
        result = "VERT"

    if result == "VERT":
        return _create_space_normal(normal)
    return _create_space_normal_tangent(normal, plane)


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
    elif pref.pivot == "CUSTOM":
        world_pivot = Vector(pref.custom_location)
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
    elif orientation == "CUSTOM":
        frame = Euler(pref.custom_rotation, "XYZ").to_matrix()
    else:  # NORMAL
        frame = _build_normal_frame(bm, mw, pref.pivot == "ACTIVE")
        if frame is None:
            frame = Matrix.Identity(3)

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
