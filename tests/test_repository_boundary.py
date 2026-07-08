import importlib
import sys
import unittest
from pathlib import Path


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXTENSION_ROOT))


class RepositoryBoundaryTests(unittest.TestCase):
    def test_app_owned_modules_are_not_part_of_extension_package(self):
        app_owned_modules = (
            "findsurface.bootstrap.app_config",
            "findsurface.bootstrap.app_point_cloud",
            "findsurface.bootstrap.app_state",
            "findsurface.bootstrap.camera",
            "findsurface.bootstrap.detection",
            "findsurface.bootstrap.native_picking",
            "findsurface.bootstrap.point_cloud",
            "findsurface.bootstrap.surface_preview",
            "findsurface.bootstrap.viewport",
            "findsurface.bootstrap.workspace",
        )

        for module_name in app_owned_modules:
            with self.subTest(module_name=module_name):
                sys.modules.pop(module_name, None)
                with self.assertRaises(ModuleNotFoundError):
                    importlib.import_module(module_name)


if __name__ == "__main__":
    unittest.main()
