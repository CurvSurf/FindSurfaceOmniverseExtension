import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = PROJECT_ROOT / "tools" / "fetch_findsurface_sdk.py"

spec = importlib.util.spec_from_file_location("fetch_findsurface_sdk", TOOL_PATH)
fetch_findsurface_sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_findsurface_sdk)


class SdkAcquisitionTests(unittest.TestCase):
    def test_platform_asset_key_normalizes_supported_platforms(self):
        self.assertEqual(fetch_findsurface_sdk.platform_asset_key("Windows", "AMD64"), "windows-x86_64")
        self.assertEqual(fetch_findsurface_sdk.platform_asset_key("Linux", "x86_64"), "linux-x86_64")

    def test_load_release_config_requires_release_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "sdk_release.json"
            config_path.write_text(
                json.dumps(
                    {
                        "release_base_url": "https://github.com/CurvSurf/FindSurfaceOmniverseExtension/releases/download",
                        "assets": {"windows-x86_64": "FindSurface.dll"},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(fetch_findsurface_sdk.SdkAcquisitionError, "release_tag"):
                fetch_findsurface_sdk.load_release_config(config_path)

    def test_acquire_sdk_release_asset_uses_release_config(self):
        payload = b"release asset bytes"
        config = {
            "release_base_url": "https://github.com/CurvSurf/FindSurfaceOmniverseExtension/releases/download",
            "release_tag": "v1.0.0",
            "assets": {"linux-x86_64": "libFindSurface.so"},
        }

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_findsurface_sdk.acquire_sdk_release_asset(
                extension_root=directory,
                asset_key="linux-x86_64",
                release_config=config,
                fetcher=lambda url: payload,
            )

            output_path = Path(directory) / "data" / "native" / "linux-x86_64" / "libFindSurface.so"
            self.assertEqual(result["path"], output_path)
            self.assertEqual(result["version"], "v1.0.0")
            self.assertEqual(
                result["url"],
                "https://github.com/CurvSurf/FindSurfaceOmniverseExtension/releases/download/v1.0.0/libFindSurface.so",
            )
            self.assertEqual(output_path.read_bytes(), payload)
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())

    def test_acquire_sdk_release_asset_rejects_missing_asset(self):
        config = {
            "release_base_url": "https://github.com/CurvSurf/FindSurfaceOmniverseExtension/releases/download",
            "release_tag": "v1.0.0",
            "assets": {},
        }

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(fetch_findsurface_sdk.SdkAcquisitionError, "no asset"):
                fetch_findsurface_sdk.acquire_sdk_release_asset(
                    extension_root=directory,
                    asset_key="windows-x86_64",
                    release_config=config,
                    fetcher=lambda url: b"",
                )

    def test_acquire_sdk_release_asset_rejects_checksum_mismatch(self):
        config = {
            "release_base_url": "https://github.com/CurvSurf/FindSurfaceOmniverseExtension/releases/download",
            "release_tag": "v1.0.0",
            "assets": {"windows-x86_64": "FindSurface.dll"},
        }

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(fetch_findsurface_sdk.SdkAcquisitionError, "checksum mismatch"):
                fetch_findsurface_sdk.acquire_sdk_release_asset(
                    extension_root=directory,
                    asset_key="windows-x86_64",
                    release_config=config,
                    sha256="0" * 64,
                    fetcher=lambda url: b"different bytes",
                )

            self.assertFalse((Path(directory) / "data" / "native" / "windows-x86_64" / "FindSurface.dll").exists())


if __name__ == "__main__":
    unittest.main()
