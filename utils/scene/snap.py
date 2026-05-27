"""Cursor snapping helpers for the custom-plane picker modal.

Given a raycast hit on an evaluated mesh, pick the closest vertex/edge/face
under the cursor and derive a plane (location, normal, in-plane direction) plus
the world-space points used to highlight that element.

Ported from the blockout addon (``ops/align/snap.py`` + ``utilsbmesh/orientation.py``)
so the rotor Mirror picker behaves the same. Reuses rotor's own ``ray_cast.visible``.
"""

import math

from mathutils import Matrix, Vector


def direction_from_normal(normal):
    """Return a unit vector perpendicular to ``normal`` (arbitrary in-plane X)."""
    up_vector = Vector((0.0, 0.0, 1.0))
    if abs(normal.dot(up_vector)) > 0.9999:
        up_vector = Vector((0.0, 1.0, 0.0))
    return normal.cross(up_vector).normalized()


def face_bbox_center(face, matrix):
    """Axis-aligned bounding-box center of a face, in world space.

    Builds an in-plane basis (X = world tangent, Y = normal x X), projects the
    face verts into it, and returns the 2D AABB center back in 3D.
    """
    normal_world = (matrix.to_3x3() @ face.normal).normalized()
    location_world = matrix @ face.calc_center_median()
    direction_world = (matrix.to_3x3() @ face.calc_tangent_edge()).normalized()

    x_axis = direction_world
    y_axis = normal_world.cross(x_axis).normalized()

    coords_2d = []
    for v in face.verts:
        rel = (matrix @ v.co) - location_world
        coords_2d.append((rel.dot(x_axis), rel.dot(y_axis)))

    min_x = min(px for px, _ in coords_2d)
    max_x = max(px for px, _ in coords_2d)
    min_y = min(py for _, py in coords_2d)
    max_y = max(py for _, py in coords_2d)

    cx = 0.5 * (min_x + max_x)
    cy = 0.5 * (min_y + max_y)
    return location_world + cx * x_axis + cy * y_axis


def find_closest_element(context, obj, hit_loc, face_idx, bm):
    """Pick the vertex, edge, or face under the cursor on a raycast hit.

    Uses a viewport-distance dependent threshold so close geometry favours
    verts/edges while distant geometry favours faces.

    Returns ``(element_type, element)`` where ``element_type`` is ``"VERT"``,
    ``"EDGE"`` or ``"FACE"``. ``element`` may be ``None`` when the face index is
    out of range and no fallback face exists.
    """
    inv_matrix = obj.matrix_world.inverted()
    local_hit = inv_matrix @ hit_loc

    region_data = context.region_data
    if region_data and hasattr(region_data, "view_distance"):
        view_distance = region_data.view_distance
    else:
        view_location = (
            region_data.view_matrix.inverted().translation
            if region_data
            else Vector((0, 0, 10))
        )
        view_distance = (view_location - hit_loc).length

    # Clamp the distance factor so thresholds scale between near/far views.
    distance_factor = min(max(view_distance / 10.0, 0.2), 2.0)
    vert_threshold = 0.05 * distance_factor
    edge_threshold = 0.08 * distance_factor

    # Out-of-range face index (instanced/modified meshes): fall back to the
    # face whose center is nearest the hit point.
    if face_idx >= len(bm.faces) or face_idx < 0:
        closest_face = None
        min_dist = float("inf")
        for face in bm.faces:
            dist = (face.calc_center_median() - local_hit).length
            if dist < min_dist:
                min_dist = dist
                closest_face = face
        if closest_face is None:
            return "FACE", None
        face = closest_face
    else:
        face = bm.faces[face_idx]

    # Closest vertex on the face.
    closest_vert = None
    min_vert_dist = float("inf")
    for vert in face.verts:
        dist = (vert.co - local_hit).length
        if dist < min_vert_dist:
            min_vert_dist = dist
            closest_vert = vert

    # Closest edge on the face (within the segment).
    closest_edge = None
    min_edge_dist = float("inf")
    for edge in face.edges:
        edge_vec = edge.verts[1].co - edge.verts[0].co
        edge_len = edge_vec.length
        if edge_len < 1e-6:
            continue
        edge_dir = edge_vec / edge_len
        proj_len = (local_hit - edge.verts[0].co).dot(edge_dir)
        if 0 <= proj_len <= edge_len:
            proj_point = edge.verts[0].co + edge_dir * proj_len
            dist = (local_hit - proj_point).length
            if dist < min_edge_dist:
                min_edge_dist = dist
                closest_edge = edge

    # Priority by view distance: prefer verts/edges when close, faces when far.
    if view_distance < 5.0:
        if min_vert_dist < vert_threshold * 1.5:
            return "VERT", closest_vert
        if min_edge_dist < edge_threshold * 1.2:
            return "EDGE", closest_edge
    elif view_distance < 15.0:
        if min_vert_dist < vert_threshold:
            return "VERT", closest_vert
        if min_edge_dist < edge_threshold:
            return "EDGE", closest_edge
    else:
        if min_vert_dist < vert_threshold * 0.5:
            return "VERT", closest_vert
        if min_edge_dist < edge_threshold * 0.7:
            return "EDGE", closest_edge

    return "FACE", face


def element_plane(matrix, element_type, element, ray):
    """Derive a plane and highlight points from a picked mesh element.

    Returns ``(location, normal, direction, hi_points)`` in world space, where
    ``hi_points`` are the world coords used to highlight the element.
    """
    inv_trans = matrix.inverted().transposed().to_3x3()

    if element_type == "VERT":
        vert = element
        location = matrix @ vert.co
        normal = inv_trans @ vert.normal
        normal.normalize()
        direction = matrix.to_3x3() @ direction_from_normal(vert.normal)
        hi_points = [location]

    elif element_type == "EDGE":
        edge = element
        v0 = matrix @ edge.verts[0].co
        v1 = matrix @ edge.verts[1].co
        location = (v0 + v1) / 2.0
        faces_normals = [inv_trans @ f.normal for f in edge.link_faces]
        sum_normal = sum(faces_normals, Vector())
        direction = v1 - v0
        direction_y = sum_normal.cross(direction)
        normal = direction.cross(direction_y)
        hi_points = [v0, v1]

    else:  # FACE
        face = element
        if face is None:
            # Instanced fallback: use the raw raycast hit data.
            location = ray.location.copy()
            normal = ray.normal.copy()
            direction = direction_from_normal(normal)
            hi_points = []
        else:
            normal = inv_trans @ face.normal
            location = face_bbox_center(face, matrix)
            direction = matrix.to_3x3() @ face.calc_tangent_edge()
            hi_points = [matrix @ loop.vert.co for loop in face.loops]

    if normal.length < 1e-9:
        normal = Vector((0.0, 0.0, 1.0))
    if direction.length < 1e-9:
        direction = direction_from_normal(normal)
    normal.normalize()
    direction.normalize()
    return location, normal, direction, hi_points


def rotation_from_vectors(normal, direction):
    """Build XYZ Euler radians from a plane normal (Z) and in-plane direction (X).

    Orthonormalizes z=normal / x=direction / y=z x x, then snaps angles within
    0.01 rad of a 90 deg multiple to exact values (matches blockout).
    """
    normal = normal.normalized()
    direction = direction.normalized()

    z_axis = normal
    x_axis = direction
    y_axis = z_axis.cross(x_axis).normalized()
    x_axis = y_axis.cross(z_axis).normalized()

    rotation_matrix = Matrix((x_axis, y_axis, z_axis)).transposed().to_3x3()
    euler = rotation_matrix.to_euler("XYZ")
    rotation = [angle for angle in euler]

    half_pi = math.pi / 2
    for i, angle in enumerate(rotation):
        if abs(angle % half_pi) < 0.01 or abs(angle % half_pi - half_pi) < 0.01:
            rotation[i] = round(angle / half_pi) * half_pi

    return rotation
