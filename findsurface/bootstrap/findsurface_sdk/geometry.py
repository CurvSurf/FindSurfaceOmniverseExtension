from math import atan2, pi, sqrt


EPSILON = 1.0e-9


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, scale):
    return (a[0] * scale, a[1] * scale, a[2] * scale)


def div(a, scale):
    if abs(scale) <= EPSILON:
        return (0.0, 0.0, 0.0)
    return (a[0] / scale, a[1] / scale, a[2] / scale)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length(a):
    return sqrt(dot(a, a))


def normalize(a, fallback=(0.0, 0.0, 1.0)):
    size = length(a)
    if size <= EPSILON:
        return fallback
    return div(a, size)


def distance(a, b):
    return length(sub(a, b))


def deterministic_perpendicular(axis):
    unit = normalize(axis)
    world_up = (0.0, 1.0, 0.0)
    world_right = (1.0, 0.0, 0.0)
    if abs(dot(unit, world_up)) < 0.9:
        return normalize(cross(world_up, unit), world_right)
    return normalize(cross(world_right, unit), (0.0, 0.0, 1.0))


def signed_angle_between(a, b, axis):
    unit_axis = normalize(axis)
    unit_a = normalize(a, deterministic_perpendicular(unit_axis))
    unit_b = normalize(b, unit_a)
    return atan2(dot(unit_axis, cross(unit_a, unit_b)), dot(unit_a, unit_b))


def absolute_angle_between(a, b, axis):
    angle = signed_angle_between(a, b, axis)
    if angle < 0.0:
        angle += 2.0 * pi
    return angle


def calculate_elbow_joint(inlier_points, center, axis, major_radius):
    unit_axis = normalize(axis)
    projected = []
    for point in inlier_points:
        offset = sub(point, center)
        direction = cross(cross(unit_axis, offset), unit_axis)
        if length(direction) > EPSILON:
            projected.append(normalize(direction))

    if not projected:
        start_direction = deterministic_perpendicular(unit_axis)
        return add(center, mul(start_direction, major_radius)), 2.0 * pi

    barycentric = (0.0, 0.0, 0.0)
    for direction in projected:
        barycentric = add(barycentric, direction)
    barycentric = div(barycentric, len(projected))

    if length(barycentric) < 0.1:
        start_direction = deterministic_perpendicular(unit_axis)
        return add(center, mul(start_direction, major_radius)), 2.0 * pi

    elbow_middle = normalize(barycentric)
    angles = [signed_angle_between(elbow_middle, direction, unit_axis) for direction in projected]
    min_index = min(range(len(angles)), key=lambda index: angles[index])
    max_index = max(range(len(angles)), key=lambda index: angles[index])
    sweep_angle = absolute_angle_between(projected[min_index], projected[max_index], unit_axis)
    if sweep_angle > 355.0 * pi / 180.0:
        sweep_angle = 2.0 * pi
    return add(center, mul(projected[min_index], major_radius)), sweep_angle


def make_transform_axes(origin, x_axis, y_axis, z_axis):
    return {
        "origin": origin,
        "x_axis": normalize(x_axis, (1.0, 0.0, 0.0)),
        "y_axis": normalize(y_axis, (0.0, 1.0, 0.0)),
        "z_axis": normalize(z_axis, (0.0, 0.0, 1.0)),
    }


def plane_frame(upper_left, upper_right, lower_left, lower_right):
    center = div(add(add(upper_left, upper_right), add(lower_left, lower_right)), 4.0)
    x_axis = normalize(sub(upper_right, upper_left), (1.0, 0.0, 0.0))
    y_candidate = normalize(sub(lower_left, upper_left), (0.0, 1.0, 0.0))
    z_axis = normalize(cross(x_axis, y_candidate), (0.0, 0.0, 1.0))
    y_axis = normalize(cross(z_axis, x_axis), y_candidate)
    return {
        **make_transform_axes(center, x_axis, y_axis, z_axis),
        "width": distance(upper_right, upper_left),
        "height": distance(lower_left, upper_left),
    }


def axis_frame(bottom, top):
    center = div(add(bottom, top), 2.0)
    y_axis = normalize(sub(top, bottom), (0.0, 1.0, 0.0))
    x_axis = deterministic_perpendicular(y_axis)
    z_axis = normalize(cross(x_axis, y_axis), (0.0, 0.0, 1.0))
    x_axis = normalize(cross(y_axis, z_axis), x_axis)
    return {
        **make_transform_axes(center, x_axis, y_axis, z_axis),
        "height": distance(top, bottom),
    }


def torus_frame(center, axis, start_tube_center):
    z_axis = normalize(axis)
    x_axis = sub(start_tube_center, center)
    x_axis = sub(x_axis, mul(z_axis, dot(x_axis, z_axis)))
    x_axis = normalize(x_axis, deterministic_perpendicular(z_axis))
    y_axis = normalize(cross(z_axis, x_axis), (0.0, 1.0, 0.0))
    return make_transform_axes(center, x_axis, y_axis, z_axis)
