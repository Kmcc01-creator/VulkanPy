from src.maths.vectors import Vector3

def ray_triangle_intersect(origin: Vector3, direction: Vector3, vertex0: Vector3, vertex1: Vector3, vertex2: Vector3):
    epsilon = 0.000001
    edge1 = vertex1 - vertex0
    edge2 = vertex2 - vertex0
    h = direction.cross(edge2)
    a = edge1.dot(h)
    if a > -epsilon and a < epsilon:
        return None  # Ray is parallel to the triangle

    f = 1.0 / a
    s = origin - vertex0
    u = f * s.dot(h)
    if u < 0.0 or u > 1.0:
        return None

    q = s.cross(edge1)
    v = f * direction.dot(q)
    if v < 0.0 or u + v > 1.0:
        return None

    # At this stage we can compute t to find out where the intersection point is on the line.
    t = f * edge2.dot(q)
    if t > epsilon:  # Ray intersection
        return t
    else:
        return None  # This means that there is a line intersection but not a ray intersection.
