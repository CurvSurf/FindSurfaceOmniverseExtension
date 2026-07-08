from enum import IntEnum


class FsFeatureType(IntEnum):
    NONE = -0x0201
    ANY = 0x0200
    PLANE = 0x0201
    SPHERE = 0x0202
    CYLINDER = 0x0203
    CONE = 0x0204
    TORUS = 0x0205


class FsFloatParameter(IntEnum):
    MEASUREMENT_ACCURACY = 0x0501
    MEAN_DISTANCE = 0x0502
    SEED_RADIUS = 0x0503


class FsIntParameter(IntEnum):
    RADIAL_EXPANSION = 0x0601
    LATERAL_EXTENSION = 0x0602
    SEED_INDEX = 0x0604


class FsBoolParameter(IntEnum):
    SMART_CONVERT_CONE_TO_CYLINDER = 0x0701
    SMART_CONVERT_TORUS_TO_SPHERE = 0x0702
    SMART_CONVERT_TORUS_TO_CYLINDER = 0x0703


FEATURE_TYPE_TO_NAME = {
    FsFeatureType.PLANE: "Plane",
    FsFeatureType.SPHERE: "Sphere",
    FsFeatureType.CYLINDER: "Cylinder",
    FsFeatureType.CONE: "Cone",
    FsFeatureType.TORUS: "Torus",
}

NAME_TO_FEATURE_TYPE = {
    "Auto": FsFeatureType.ANY,
    "Plane": FsFeatureType.PLANE,
    "Sphere": FsFeatureType.SPHERE,
    "Cylinder": FsFeatureType.CYLINDER,
    "Cone": FsFeatureType.CONE,
    "Torus": FsFeatureType.TORUS,
}
