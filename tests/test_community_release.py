"""Archive integrity and release-boundary checks without a runtime or network."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

CORE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("community_release_tool", CORE / "tools/prepare_community_release.py")
tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tool
spec.loader.exec_module(tool)


class CommunityReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "source"
        self.root.mkdir()
        self.config = dict(repository="CurvSurf/Fixture", release_tag="v1.1.0", extension_id="com.findsurface.bootstrap", kind="core", kit_version="110.1.2")
        (self.root / "community_release.json").write_text(json.dumps(self.config))
        for name in ("config", "docs", "data", "findsurface", ".agents", "tests"):
            (self.root / name).mkdir()
        (self.root / ".agents/private.txt").write_text("must not be packaged")
        (self.root / "tests/test_fixture.py").touch()
        config = '''[package]
name="com.findsurface.bootstrap"
title="Fixture"
description="Fixture core"
category="other"
version="1.1.0"
repository="https://github.com/CurvSurf/Fixture"
authors=["CurvSurf"]
keywords=["findsurface"]
readme="docs/Overview.md"
changelog="docs/CHANGELOG.md"
icon="data/icon.svg"
preview_image="data/preview.svg"
[package.target]
kit=["110.1.2"]
platform=["windows-x86_64", "linux-x86_64"]
'''
        (self.root / "config/extension.toml").write_text(config)
        for rel in ("docs/Overview.md", "docs/CHANGELOG.md", "data/icon.svg", "data/preview.svg"):
            (self.root / rel).write_text("1.1.0")
        pe = bytearray(128)
        pe[:2] = b"MZ"
        struct.pack_into("<I", pe, 60, 64)
        pe[64:68] = b"PE\0\0"
        struct.pack_into("<H", pe, 68, 0x8664)
        native = self.root / "data/native/windows-x86_64/FindSurface.dll"
        native.parent.mkdir(parents=True)
        native.write_bytes(pe)
        (self.root / "config/sdk_release.json").write_text(json.dumps({"release_base_url": "https://github.com/CurvSurf/FindSurfaceOmniverseExtension/releases/download", "release_tag": "v1.0.1", "assets": {"windows-x86_64": "FindSurface.dll"}, "sha256": {"windows-x86_64": hashlib.sha256(pe).hexdigest()}}))

    def test_reproducible_archive_excludes_private_and_development_files(self):
        first = tool.prepare(self.root, self.base / "first", "windows-x86_64")
        second = tool.prepare(self.root, self.base / "second", "windows-x86_64")
        self.assertEqual(first.name, "CurvSurf-Fixture-windows-x86_64-v1.1.0.zip")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as zipped:
            self.assertFalse(any(".agents" in name or "/tests/" in name for name in zipped.namelist()))

    def test_modified_archive_is_rejected(self):
        archive = tool.prepare(self.root, self.base / "built", "windows-x86_64")
        archive.write_bytes(archive.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            tool.verify_archive(archive.parent)

    def test_unapproved_platform_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not approved"):
            tool.prepare(self.root, self.base / "built", "linux-x86_64")

    def test_wrong_registry_category_is_rejected(self):
        config = self.root / "config/extension.toml"
        config.write_text(config.read_text().replace('category="other"', 'category="Geometry"'))
        with self.assertRaisesRegex(ValueError, "Expected category other"):
            tool.prepare(self.root, self.base / "built", "windows-x86_64")

    def test_missing_sdk_binary_can_be_packaged(self):
        (self.root / "data/native/windows-x86_64/FindSurface.dll").unlink()
        archive = tool.prepare(self.root, self.base / "built", "windows-x86_64")
        self.assertEqual(tool.verify_archive(archive.parent)["sdk"]["delivery"], "download-on-first-use")

    def test_existing_sdk_binary_is_excluded_even_if_not_release_bytes(self):
        (self.root / "data/native/windows-x86_64/FindSurface.dll").write_bytes(b"local development SDK")
        archive = tool.prepare(self.root, self.base / "built", "windows-x86_64")
        with zipfile.ZipFile(archive) as zipped:
            self.assertFalse(any(Path(n).name in tool.SDK_FILENAMES for n in zipped.namelist()))

    def test_missing_download_checksum_is_rejected(self):
        path = self.root / "config/sdk_release.json"
        policy = json.loads(path.read_text())
        policy["sha256"] = {}
        path.write_text(json.dumps(policy))
        with self.assertRaisesRegex(ValueError, "SDK download SHA256"):
            tool.prepare(self.root, self.base / "built", "windows-x86_64")


if __name__ == "__main__":
    unittest.main()
