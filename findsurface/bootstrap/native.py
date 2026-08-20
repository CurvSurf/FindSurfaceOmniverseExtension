from dataclasses import dataclass
from itertools import count
from threading import Lock

from .findsurface_sdk.abi import vec3
from .findsurface_sdk.constants import (
    FEATURE_TYPE_TO_NAME,
    NAME_TO_FEATURE_TYPE,
    FsBoolParameter,
    FsFloatParameter,
    FsIntParameter,
)
from .findsurface_sdk.geometry import axis_frame, calculate_elbow_joint, plane_frame, torus_frame
from .findsurface_sdk.wrapper import FindSurfaceSdk, FindSurfaceSdkError, is_valid_result
from .results import FindSurfaceResult


MAX_POINTS = 200_000
DETECTION_TYPES = ("Auto", "Plane", "Sphere", "Cylinder", "Cone", "Torus")
SMART_CONVERSION_PARAMETERS = (
    FsBoolParameter.SMART_CONVERT_CONE_TO_CYLINDER,
    FsBoolParameter.SMART_CONVERT_TORUS_TO_SPHERE,
    FsBoolParameter.SMART_CONVERT_TORUS_TO_CYLINDER,
)


class FindSurfaceError(Exception):
    pass


class ValidationError(FindSurfaceError):
    pass


@dataclass(frozen=True)
class DetectionOptions:
    detection_type: str = "Auto"
    seed_radius: float = 1.0
    measurement_accuracy: float = 0.02
    mean_distance: float = 0.05
    radial_expansion: int = 5
    lateral_extension: int = 5

    def validate(self):
        if self.detection_type not in DETECTION_TYPES:
            raise ValidationError(f"Unsupported detection type: {self.detection_type}")
        for name, value in (
            ("Seed Radius", self.seed_radius),
            ("Measurement Accuracy", self.measurement_accuracy),
            ("Mean Distance", self.mean_distance),
        ):
            if value <= 0:
                raise ValidationError(f"{name} must be greater than 0.")
        for name, value in (("Radial Expansion", self.radial_expansion), ("Lateral Extension", self.lateral_extension)):
            if value < 0 or value > 10:
                raise ValidationError(f"{name} must be between 0 and 10.")


@dataclass
class _PreparedPointCloud:
    active_original_indices: list[int]
    active_index_by_original: dict[int, int]
    active_points: list[tuple[float, float, float]]
    point_array: object | None = None
    point_count: int = 0


class NativeFindSurfaceProvider:
    def __init__(self, sdk=None):
        self._sdk = sdk or FindSurfaceSdk()
        self._ids = count(1)
        self._prepared_cache_key = None
        self._prepared_cache = None
        self._context_lock = Lock()
        self._context = self._sdk.create_context()

    def close(self):
        with self._context_lock:
            context = self._context
            self._context = None
            self._prepared_cache_key = None
            self._prepared_cache = None
            if context is not None:
                self._sdk.release_context(context)

    def detect(self, points, active_mask, seed_index, options, active_generation=None):
        if len(points) > MAX_POINTS:
            raise FindSurfaceError("This FindSurface build supports up to 200,000 points.")
        options.validate()
        if seed_index < 0 or seed_index >= len(points):
            raise ValueError("Seed index is outside the point cloud.")
        if not active_mask[seed_index]:
            raise ValueError("Seed point is no longer active.")

        with self._context_lock:
            context = self._context
            if context is None:
                raise FindSurfaceError("FindSurface provider is closed.")

            prepared = self._prepare_pointcloud(points, active_mask, active_generation)
            active_original_indices = prepared.active_original_indices
            try:
                active_seed_index = prepared.active_index_by_original[seed_index]
            except KeyError as exc:
                raise ValueError("Seed point is no longer active.") from exc
            feature_type = NAME_TO_FEATURE_TYPE[options.detection_type]

            self._apply_options(context, options, active_seed_index)
            point_array = self._set_prepared_pointcloud(context, prepared)
            raw_result = self._sdk.find(context, feature_type)
            if not is_valid_result(raw_result):
                raise FindSurfaceSdkError(
                    f"FindSurface did not return a valid result. result_type={raw_result.result_type}, "
                    f"rms_error={float(raw_result.rms_error):g}"
                )
            result_type = FEATURE_TYPE_TO_NAME.get(type(feature_type)(raw_result.result_type))
            if not result_type:
                raise FindSurfaceSdkError(f"Unsupported FindSurface result type: {raw_result.result_type}")
            flags = self._sdk.get_outlier_flags(context, prepared.point_count)

            inlier_indices = [
                active_original_indices[index]
                for index, flag in enumerate(flags)
                if flag == 0 and index < len(active_original_indices)
            ]
            if not inlier_indices:
                raise FindSurfaceSdkError("FindSurface returned no inlier points.")

            inlier_points = [tuple(points[index]) for index in inlier_indices]
            parameters = convert_raw_result(raw_result, result_type, inlier_points)
            serial = next(self._ids)
            return FindSurfaceResult(
                id=f"{result_type}_{serial:03d}",
                type=result_type,
                seed_index=seed_index,
                seed_position=tuple(points[seed_index]),
                inlier_indices=inlier_indices,
                active_generation=int(active_generation or 0),
                measurement_accuracy=options.measurement_accuracy,
                rms_error=float(raw_result.rms_error),
                parameters=parameters,
            )

    def _prepare_pointcloud(self, points, active_mask, active_generation=None):
        cache_key = None
        if active_generation is not None:
            cache_key = (id(points), len(points), id(active_mask), len(active_mask), active_generation)
            if cache_key == self._prepared_cache_key and self._prepared_cache is not None:
                return self._prepared_cache

        active_original_indices = [index for index, active in enumerate(active_mask) if active]
        active_index_by_original = {
            original_index: active_index for active_index, original_index in enumerate(active_original_indices)
        }
        active_points = [tuple(points[index]) for index in active_original_indices]
        prepared = _PreparedPointCloud(
            active_original_indices=active_original_indices,
            active_index_by_original=active_index_by_original,
            active_points=active_points,
            point_count=len(active_points),
        )
        if hasattr(self._sdk, "build_pointcloud_buffer"):
            prepared.point_array, prepared.point_count = self._sdk.build_pointcloud_buffer(active_points)

        if cache_key is not None:
            self._prepared_cache_key = cache_key
            self._prepared_cache = prepared
        return prepared

    def _set_prepared_pointcloud(self, context, prepared):
        if prepared.point_array is not None and hasattr(self._sdk, "set_pointcloud_buffer"):
            return self._sdk.set_pointcloud_buffer(context, prepared.point_array, prepared.point_count)
        return self._sdk.set_pointcloud(context, prepared.active_points)

    def _apply_options(self, context, options, active_seed_index):
        self._sdk.set_float(context, FsFloatParameter.MEASUREMENT_ACCURACY, options.measurement_accuracy)
        self._sdk.set_float(context, FsFloatParameter.MEAN_DISTANCE, options.mean_distance)
        self._sdk.set_float(context, FsFloatParameter.SEED_RADIUS, options.seed_radius)
        for parameter in SMART_CONVERSION_PARAMETERS:
            self._sdk.set_boolean(context, parameter, True)
        self._sdk.set_int(context, FsIntParameter.RADIAL_EXPANSION, options.radial_expansion | 0x0100)
        self._sdk.set_int(context, FsIntParameter.LATERAL_EXTENSION, options.lateral_extension | 0x0100)
        self._sdk.set_int(context, FsIntParameter.SEED_INDEX, active_seed_index)


def convert_raw_result(raw_result, result_type, inlier_points):
    if result_type == "Plane":
        plane = raw_result.plane_result
        lower_left = vec3(plane.lower_left)
        lower_right = vec3(plane.lower_right)
        upper_right = vec3(plane.upper_right)
        upper_left = vec3(plane.upper_left)
        return {
            **plane_frame(upper_left, upper_right, lower_left, lower_right),
            "upper_left": upper_left,
            "upper_right": upper_right,
            "lower_left": lower_left,
            "lower_right": lower_right,
        }
    if result_type == "Sphere":
        sphere = raw_result.sphere_result
        center = vec3(sphere.center)
        return {"center": center, "origin": center, "radius": float(sphere.radius)}
    if result_type == "Cylinder":
        cylinder = raw_result.cylinder_result
        bottom = vec3(cylinder.bottom)
        top = vec3(cylinder.top)
        return {**axis_frame(bottom, top), "bottom": bottom, "top": top, "radius": float(cylinder.radius)}
    if result_type == "Cone":
        cone = raw_result.cone_result
        bottom = vec3(cone.bottom)
        top = vec3(cone.top)
        return {
            **axis_frame(bottom, top),
            "bottom": bottom,
            "top": top,
            "bottom_radius": float(cone.bottom_radius),
            "top_radius": float(cone.top_radius),
        }
    if result_type == "Torus":
        torus = raw_result.torus_result
        center = vec3(torus.center)
        axis = vec3(torus.axis)
        major_radius = float(torus.mean_radius)
        start_tube_center, sweep_angle = calculate_elbow_joint(inlier_points, center, axis, major_radius)
        return {
            **torus_frame(center, axis, start_tube_center),
            "center": center,
            "axis": axis,
            "major_radius": major_radius,
            "tube_radius": float(torus.tube_radius),
            "start_tube_center": start_tube_center,
            "sweep_angle": sweep_angle,
        }
    raise ValueError(f"Unsupported FindSurface result type: {result_type}")


__all__ = [
    "DETECTION_TYPES",
    "MAX_POINTS",
    "DetectionOptions",
    "FindSurfaceError",
    "FindSurfaceSdkError",
    "NativeFindSurfaceProvider",
    "ValidationError",
    "convert_raw_result",
]
