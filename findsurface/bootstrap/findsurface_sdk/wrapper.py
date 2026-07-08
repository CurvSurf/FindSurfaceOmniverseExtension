import ctypes
import hashlib
import json
import math
import os
import platform
import urllib.request
from pathlib import Path

from .abi import Float3, FsResult
from .constants import FsFeatureType, FsFloatParameter, FsIntParameter


class FindSurfaceSdkError(RuntimeError):
    pass


class FindSurfaceSdk:
    def __init__(self, library_path=None):
        explicit_library_path = library_path is not None
        self.library_path = Path(library_path) if library_path else default_library_path()
        if not explicit_library_path and not self.library_path.exists():
            ensure_default_library()
        if not self.library_path.exists():
            raise FileNotFoundError(f"FindSurface native library was not found: {self.library_path}")
        self._lib = ctypes.CDLL(str(self.library_path))
        self._bind_functions()

    def create_context(self):
        context = self._lib.fs_create_context(False)
        if not context:
            raise FindSurfaceSdkError("fs_create_context returned NULL.")
        return context

    def release_context(self, context):
        if context:
            self._lib.fs_release_context(context)

    def set_float(self, context, parameter, value):
        self._lib.fs_set_float(context, int(parameter), ctypes.c_float(float(value)))

    def set_int(self, context, parameter, value):
        self._lib.fs_set_int(context, int(parameter), int(value))

    def set_boolean(self, context, parameter, value):
        self._lib.fs_set_boolean(context, int(parameter), bool(value))

    def get_boolean(self, context, parameter):
        return bool(self._lib.fs_get_boolean(context, int(parameter)))

    def set_pointcloud(self, context, points):
        point_array, point_count = self.build_pointcloud_buffer(points)
        self.set_pointcloud_buffer(context, point_array, point_count)
        return point_array

    def build_pointcloud_buffer(self, points):
        point_count = len(points)
        array_type = Float3 * point_count
        point_array = array_type(*[Float3(float(point[0]), float(point[1]), float(point[2])) for point in points])
        return point_array, point_count

    def set_pointcloud_buffer(self, context, point_array, point_count):
        self._lib.fs_set_pointcloud(
            context,
            ctypes.cast(point_array, ctypes.c_void_p),
            0,
            point_count,
            ctypes.sizeof(Float3),
            False,
        )
        return point_array

    def find(self, context, feature_type):
        result = FsResult()
        if feature_type == FsFeatureType.ANY:
            self._lib.fs_find_surface(context, int(feature_type), ctypes.byref(result))
        elif feature_type == FsFeatureType.PLANE:
            self._lib.fs_find_plane(context, ctypes.byref(result))
        elif feature_type == FsFeatureType.SPHERE:
            self._lib.fs_find_sphere(context, ctypes.byref(result))
        elif feature_type == FsFeatureType.CYLINDER:
            self._lib.fs_find_cylinder(context, ctypes.byref(result))
        elif feature_type == FsFeatureType.CONE:
            self._lib.fs_find_cone(context, ctypes.byref(result))
        elif feature_type == FsFeatureType.TORUS:
            self._lib.fs_find_torus(context, ctypes.byref(result))
        else:
            raise ValueError(f"Unsupported FindSurface feature type: {feature_type}")
        return result

    def get_outlier_flags(self, context, point_count):
        flags = (ctypes.c_uint8 * point_count)()
        self._lib.fs_get_outlier_flags(context, flags, 0, point_count)
        return [int(flags[index]) for index in range(point_count)]

    def _bind_functions(self):
        self._lib.fs_create_context.argtypes = [ctypes.c_bool]
        self._lib.fs_create_context.restype = ctypes.c_void_p
        self._lib.fs_release_context.argtypes = [ctypes.c_void_p]
        self._lib.fs_release_context.restype = None

        self._lib.fs_set_float.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_float]
        self._lib.fs_set_float.restype = None
        self._lib.fs_set_int.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        self._lib.fs_set_int.restype = None
        self._lib.fs_set_boolean.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_bool]
        self._lib.fs_set_boolean.restype = None
        self._lib.fs_get_boolean.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._lib.fs_get_boolean.restype = ctypes.c_bool

        self._lib.fs_set_pointcloud.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_bool,
        ]
        self._lib.fs_set_pointcloud.restype = None

        self._lib.fs_find_surface.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(FsResult)]
        self._lib.fs_find_surface.restype = None
        self._lib.fs_find_plane.argtypes = [ctypes.c_void_p, ctypes.POINTER(FsResult)]
        self._lib.fs_find_plane.restype = None
        self._lib.fs_find_sphere.argtypes = [ctypes.c_void_p, ctypes.POINTER(FsResult)]
        self._lib.fs_find_sphere.restype = None
        self._lib.fs_find_cylinder.argtypes = [ctypes.c_void_p, ctypes.POINTER(FsResult)]
        self._lib.fs_find_cylinder.restype = None
        self._lib.fs_find_cone.argtypes = [ctypes.c_void_p, ctypes.POINTER(FsResult)]
        self._lib.fs_find_cone.restype = None
        self._lib.fs_find_torus.argtypes = [ctypes.c_void_p, ctypes.POINTER(FsResult)]
        self._lib.fs_find_torus.restype = None
        self._lib.fs_get_outlier_flags.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
            ctypes.c_int,
        ]
        self._lib.fs_get_outlier_flags.restype = None


def default_library_path():
    extension_root = Path(__file__).resolve().parents[3]
    system = platform.system().lower()
    if system == "windows":
        return extension_root / "data" / "native" / "windows-x86_64" / "FindSurface.dll"
    if system == "linux":
        return extension_root / "data" / "native" / "linux-x86_64" / "libFindSurface.so"
    raise RuntimeError(f"Unsupported FindSurface SDK platform: {platform.system()}")


def ensure_default_library():
    if not _auto_download_enabled():
        return False

    library_path = default_library_path()
    if library_path.exists():
        return True

    asset_key = _platform_asset_key()
    asset_name = _release_asset_name(asset_key)
    release_base_url = _release_base_url()
    release_tag = _release_tag()
    url = f"{release_base_url}/{release_tag}/{asset_name}"

    library_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers=_download_headers())
    with urllib.request.urlopen(request) as response:
        payload = response.read()

    expected_sha256 = _expected_sha256(asset_key)
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if expected_sha256 and actual_sha256.lower() != expected_sha256.lower():
        raise FindSurfaceSdkError(
            f"FindSurface SDK checksum mismatch for {asset_key}: expected {expected_sha256}, got {actual_sha256}."
        )

    library_path.write_bytes(payload)
    return True


def _auto_download_enabled():
    value = os.environ.get("FINDSURFACE_SDK_AUTO_DOWNLOAD", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _platform_asset_key():
    system = platform.system().lower()
    if system == "windows":
        return "windows-x86_64"
    if system == "linux":
        return "linux-x86_64"
    raise RuntimeError(f"Unsupported FindSurface SDK platform: {platform.system()}")


def _release_asset_name(asset_key):
    asset_name = (_release_config().get("assets") or {}).get(asset_key)
    if asset_name:
        return asset_name
    raise FindSurfaceSdkError(f"FindSurface SDK release config has no asset for {asset_key}.")


def _release_base_url():
    value = _release_config().get("release_base_url")
    if value:
        return str(value).rstrip("/")
    raise FindSurfaceSdkError("FindSurface SDK release config must include release_base_url.")


def _release_tag():
    value = _release_config().get("release_tag")
    if value:
        return str(value).strip()
    raise FindSurfaceSdkError("FindSurface SDK release config must include release_tag.")


def _release_config():
    path = _release_config_path()
    try:
        with path.open("r", encoding="utf-8") as stream:
            config = json.load(stream)
    except OSError as exc:
        raise FindSurfaceSdkError(f"FindSurface SDK release config could not be read: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FindSurfaceSdkError(f"FindSurface SDK release config is invalid JSON: {path}") from exc
    if not isinstance(config, dict):
        raise FindSurfaceSdkError(f"FindSurface SDK release config must be a JSON object: {path}")
    return config


def _release_config_path():
    return Path(__file__).resolve().parents[3] / "config" / "sdk_release.json"


def _expected_sha256(asset_key):
    if os.environ.get("FINDSURFACE_SDK_SHA256"):
        return os.environ["FINDSURFACE_SDK_SHA256"]
    env_name = "FINDSURFACE_SDK_SHA256_" + asset_key.upper().replace("-", "_")
    return os.environ.get(env_name)


def _download_headers():
    token = os.environ.get("FINDSURFACE_SDK_TOKEN")
    if token:
        scheme = os.environ.get("FINDSURFACE_SDK_AUTH_SCHEME", "Bearer").strip() or "Bearer"
        return {"Authorization": f"{scheme} {token}"}
    return {}


def is_valid_result(result):
    return result.result_type > 0 and math.isfinite(float(result.rms_error)) and float(result.rms_error) >= 0.0
