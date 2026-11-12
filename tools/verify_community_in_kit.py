"""Run with Kit --exec; calls validation functions only, never publish APIs.

Configure /findsurface/communityVerification/output and optionally the string
array /findsurface/communityVerification/extensions in the test host .kit file.
The default checks only the core. Add release stage/exts folders to the host.
"""
import asyncio
import gc
import json
from pathlib import Path
import traceback

import carb.settings
import omni.kit.app


async def check():
    app = omni.kit.app.get_app()
    settings = carb.settings.get_settings()
    root = "/findsurface/communityVerification"
    output = settings.get_as_string(root + "/output")
    if not output:
        app.post_quit(1)
        raise ValueError("Set /findsurface/communityVerification/output to a local report path")
    names = settings.get(root + "/extensions") or ["com.findsurface.bootstrap"]
    report = {"published": False, "checks": {}}
    try:
        for _ in range(10):
            await app.next_update_async()
        from omni.kit.registry.nucleus.verification import (
            verify_extension_for_publishing, verify_and_get_package_id_for_publishing,
        )
        settings.set_bool("/app/extensions/skipPublishVerification", False)
        manager = app.get_extension_manager()
        for name in names:
            if not manager.set_extension_enabled_immediate(name, True):
                raise ValueError(f"Could not enable {name}")
            metadata = manager.get_extension_dict(manager.get_enabled_extension_id(name))
            package_id = verify_and_get_package_id_for_publishing(metadata)
            valid, _ = verify_extension_for_publishing(metadata)
            if not valid:
                raise ValueError(f"Kit publication verification failed: {name}")
            report["checks"][name] = {"verified": True, "package_id": package_id,
                                       "version": metadata["package"]["version"]}
        for main in ("com.curvsurf.findsurface_omniverse", "com.curvsurf.findsurface_isaac_sim"):
            if manager.is_extension_enabled(main):
                raise ValueError("A demo implementation was enabled in the host")
        from findsurface.bootstrap.demo_launcher_ui import DemoLauncherWindow
        windows = [item for item in gc.get_objects() if type(item) is DemoLauncherWindow]
        if any(window.child.running for window in windows):
            raise ValueError("Enabling a launcher started a child without a button click")
        report.update(ok=True, launcher_windows=len(windows), demo_not_enabled_in_host=True)
    except Exception:
        report.update(ok=False, error=traceback.format_exc())
    Path(output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    app.post_quit(0 if report.get("ok") else 1)


asyncio.ensure_future(check())
