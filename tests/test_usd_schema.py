import sys
import unittest
from pathlib import Path


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXTENSION_ROOT))


from findsurface.bootstrap import usd_schema  # noqa: E402


class UsdSchemaTests(unittest.TestCase):
    def test_schema_plugin_resources_are_discoverable(self):
        root = usd_schema.schema_plugin_root()

        self.assertTrue(root.exists())
        self.assertEqual(root.name, usd_schema.SCHEMA_PLUGIN_NAME)
        self.assertTrue((root / "resources" / "plugInfo.json").exists())
        self.assertTrue((root / "resources" / "generatedSchema.usda").exists())

    def test_api_schema_metadata_lines_use_role_specific_schema(self):
        self.assertEqual(
            usd_schema.api_schemas_metadata_lines(usd_schema.ROLE_GEOMETRY_EXPORT, indent=4),
            ['    prepend apiSchemas = ["FindSurfaceGeometryExportAPI"]'],
        )
        self.assertEqual(usd_schema.api_schemas_metadata_lines("unknown"), [])


if __name__ == "__main__":
    unittest.main()
