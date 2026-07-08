import ctypes
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXTENSION_ROOT))


from findsurface.bootstrap.findsurface_sdk import wrapper  # noqa: E402


class SdkWrapperTests(unittest.TestCase):
    def test_bind_functions_declares_core_abi_signatures(self):
        function_names = (
            "fs_create_context",
            "fs_release_context",
            "fs_set_float",
            "fs_set_int",
            "fs_set_boolean",
            "fs_get_boolean",
            "fs_set_pointcloud",
            "fs_find_surface",
            "fs_find_plane",
            "fs_find_sphere",
            "fs_find_cylinder",
            "fs_find_cone",
            "fs_find_torus",
            "fs_get_outlier_flags",
        )
        sdk = object.__new__(wrapper.FindSurfaceSdk)
        sdk._lib = types.SimpleNamespace(**{name: types.SimpleNamespace() for name in function_names})

        sdk._bind_functions()

        self.assertEqual(sdk._lib.fs_create_context.argtypes, [ctypes.c_bool])
        self.assertIs(sdk._lib.fs_create_context.restype, ctypes.c_void_p)
        self.assertEqual(sdk._lib.fs_set_float.argtypes, [ctypes.c_void_p, ctypes.c_int, ctypes.c_float])
        self.assertEqual(sdk._lib.fs_set_int.argtypes, [ctypes.c_void_p, ctypes.c_int, ctypes.c_int])
        self.assertEqual(sdk._lib.fs_set_boolean.argtypes, [ctypes.c_void_p, ctypes.c_int, ctypes.c_bool])
        self.assertEqual(
            sdk._lib.fs_set_pointcloud.argtypes,
            [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_bool],
        )
        self.assertEqual(sdk._lib.fs_find_surface.argtypes, [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(wrapper.FsResult)])
        self.assertEqual(sdk._lib.fs_find_plane.argtypes, [ctypes.c_void_p, ctypes.POINTER(wrapper.FsResult)])
        self.assertEqual(sdk._lib.fs_get_outlier_flags.argtypes[0], ctypes.c_void_p)
        self.assertEqual(sdk._lib.fs_get_outlier_flags.argtypes[1], ctypes.POINTER(ctypes.c_uint8))

    def test_default_library_path_uses_extension_windows_binary_location(self):
        extension_root = Path(wrapper.__file__).resolve().parents[3]

        with patch.object(wrapper.platform, "system", return_value="Windows"):
            path = wrapper.default_library_path()

        self.assertEqual(path, extension_root / "data" / "native" / "windows-x86_64" / "FindSurface.dll")

    def test_default_library_path_uses_extension_linux_binary_location(self):
        extension_root = Path(wrapper.__file__).resolve().parents[3]

        with patch.object(wrapper.platform, "system", return_value="Linux"):
            path = wrapper.default_library_path()

        self.assertEqual(path, extension_root / "data" / "native" / "linux-x86_64" / "libFindSurface.so")

    def test_default_library_path_rejects_unsupported_platform(self):
        with patch.object(wrapper.platform, "system", return_value="Darwin"):
            with self.assertRaisesRegex(RuntimeError, "Unsupported FindSurface SDK platform: Darwin"):
                wrapper.default_library_path()

    def test_constructor_reports_missing_native_library_path(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_path = Path(directory) / "FindSurface.dll"

            with self.assertRaises(FileNotFoundError) as context:
                wrapper.FindSurfaceSdk(library_path=missing_path)

        message = str(context.exception)
        self.assertIn("FindSurface native library was not found", message)
        self.assertIn(str(missing_path), message)


if __name__ == "__main__":
    unittest.main()
