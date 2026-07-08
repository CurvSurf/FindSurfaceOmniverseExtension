import ctypes


Float3 = ctypes.c_float * 3


class FsPlaneResult(ctypes.Structure):
    _fields_ = [
        ("lower_left", Float3),
        ("lower_right", Float3),
        ("upper_right", Float3),
        ("upper_left", Float3),
        ("vector4", Float3),
        ("scalar0", ctypes.c_float),
        ("scalar1", ctypes.c_float),
    ]


class FsSphereResult(ctypes.Structure):
    _fields_ = [
        ("center", Float3),
        ("vector1", Float3),
        ("vector2", Float3),
        ("vector3", Float3),
        ("vector4", Float3),
        ("radius", ctypes.c_float),
        ("scalar1", ctypes.c_float),
    ]


class FsCylinderResult(ctypes.Structure):
    _fields_ = [
        ("bottom", Float3),
        ("top", Float3),
        ("vector2", Float3),
        ("vector3", Float3),
        ("vector4", Float3),
        ("radius", ctypes.c_float),
        ("scalar1", ctypes.c_float),
    ]


class FsConeResult(ctypes.Structure):
    _fields_ = [
        ("bottom", Float3),
        ("top", Float3),
        ("vector2", Float3),
        ("vector3", Float3),
        ("vector4", Float3),
        ("bottom_radius", ctypes.c_float),
        ("top_radius", ctypes.c_float),
    ]


class FsTorusResult(ctypes.Structure):
    _fields_ = [
        ("center", Float3),
        ("axis", Float3),
        ("vector2", Float3),
        ("vector3", Float3),
        ("vector4", Float3),
        ("mean_radius", ctypes.c_float),
        ("tube_radius", ctypes.c_float),
    ]


class FsResultUnion(ctypes.Union):
    _fields_ = [
        ("plane_result", FsPlaneResult),
        ("sphere_result", FsSphereResult),
        ("cylinder_result", FsCylinderResult),
        ("cone_result", FsConeResult),
        ("torus_result", FsTorusResult),
    ]


class FsResult(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [
        ("result_type", ctypes.c_int),
        ("rms_error", ctypes.c_float),
        ("data", FsResultUnion),
    ]


def vec3(value):
    return (float(value[0]), float(value[1]), float(value[2]))
