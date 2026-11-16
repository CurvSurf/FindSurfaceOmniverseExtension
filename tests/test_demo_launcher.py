"""Runtime isolation and relocated payload regression tests; no Kit required."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from findsurface.bootstrap.demo_launcher import DemoProcess, DemoSpec, inspect_runtime, make_launch_plan, stage_launcher


class DemoLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "checkout with spaces"
        self.launcher = self.project / "source/extensions/test.launcher"
        self.launcher.joinpath("config").mkdir(parents=True)
        self.spec = DemoSpec("test.launcher", "Demo", "test.demo", "demo.kit", "kit", "110.1.2")
        self.launcher.joinpath("config/demo.json").write_text(json.dumps(self.spec.__dict__))
        self.launcher.joinpath("config/extension.toml").write_text('[dependencies]\n"curvsurf.findsurface.core" = {}\n')
        apps = self.project / "source/apps"
        apps.mkdir()
        apps.joinpath("demo.kit").write_text('[dependencies]\n"test.demo" = {}\n')
        for name in ("test.demo", "curvsurf.findsurface.core"):
            folder = self.project / "source/extensions" / name / "config"
            folder.mkdir(parents=True)
            folder.joinpath("extension.toml").write_text('[package]\nversion="1.0.0"\n')
        self.runtime = self.base / "runtime with spaces/kit"
        self.runtime.joinpath("kernel/config").mkdir(parents=True)
        self.runtime.joinpath("kernel/config/kit-core.json").write_text(json.dumps({"crashreporter": {"data": {"buildVersion": "110.1.2"}}}))
        self.runtime.joinpath("kit.exe" if os.name == "nt" else "kit").touch()
        self.runtime.parent.joinpath("extscache").mkdir()

    def test_relocated_payload_uses_no_checkout_paths(self):
        destination = self.base / "installed extension/test.launcher"
        stage_launcher(self.project, self.spec.launcher_id, destination)
        plan = make_launch_plan(destination, str(self.runtime))
        self.assertTrue(Path(plan.command[1]).is_relative_to(destination))
        self.assertFalse(any(str(self.project) in arg for arg in plan.command))
        self.assertIn(str(self.runtime.parent / "extscache"), plan.command)
        self.assertEqual(Path(plan.command[1]).read_bytes(), (self.project / "source/apps/demo.kit").read_bytes())

    def test_explicit_incompatible_runtime_does_not_fall_back(self):
        self.runtime.joinpath("kernel/config/kit-core.json").write_text('{}')
        with self.assertRaises(ValueError):
            make_launch_plan(self.launcher, str(self.runtime))

    def test_isaac_runtime_validates_product_version(self):
        spec = DemoSpec("test.launcher", "Demo", "test.demo", "demo.kit", "isaac", "6.0.1")
        self.runtime.parent.joinpath("VERSION").write_text("6.0.1-rc.7+release.test")
        root, executable = inspect_runtime(self.runtime, spec)
        self.assertEqual(root, self.runtime.parent)
        self.assertEqual(executable.parent, self.runtime)
        self.runtime.parent.joinpath("VERSION").write_text("6.1.0")
        with self.assertRaises(ValueError):
            inspect_runtime(self.runtime, spec)

    def test_missing_demo_payload_is_rejected_before_spawn(self):
        self.project.joinpath("source/extensions/test.demo/config/extension.toml").unlink()
        with self.assertRaisesRegex(ValueError, "payload file is missing"):
            make_launch_plan(self.launcher, str(self.runtime))

    def test_process_uses_argument_list_and_rejects_duplicate_running_child(self):
        plan = make_launch_plan(self.launcher, str(self.runtime))
        child = Mock()
        child.poll.return_value = None
        with patch("findsurface.bootstrap.demo_launcher.subprocess.Popen", return_value=child) as popen:
            process = DemoProcess()
            self.assertIs(process.start(plan), child)
            with self.assertRaises(ValueError):
                process.start(plan)
            self.assertEqual(popen.call_count, 1)
            self.assertEqual(popen.call_args.args[0], list(plan.command))
            self.assertNotIn("shell", popen.call_args.kwargs)

    def test_staging_does_not_overwrite_an_existing_installation(self):
        with self.assertRaises(ValueError):
            stage_launcher(self.project, self.spec.launcher_id, self.launcher)

    def test_staging_bundles_recorded_private_sdk_without_original_path_dependency(self):
        sdk = self.base / "private sdk" / "custom-library-name.bin"
        sdk.parent.mkdir()
        sdk.write_bytes(b"local SDK fixture")
        manifest = self.project / ".installation/manifest.json"
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({"sdk": {"path": str(sdk)}}))
        source_plan = make_launch_plan(self.launcher, str(self.runtime))
        self.assertIn(("FINDSURFACE_APP_SDK_PATH", str(sdk)), source_plan.environment)
        destination = self.base / "relocated/test.launcher"
        stage_launcher(self.project, self.spec.launcher_id, destination)
        plan = make_launch_plan(destination, str(self.runtime))
        bundled = Path(dict(plan.environment)["FINDSURFACE_APP_SDK_PATH"])
        self.assertTrue(bundled.is_relative_to(destination))
        self.assertEqual(bundled.read_bytes(), sdk.read_bytes())


if __name__ == "__main__":
    unittest.main()
