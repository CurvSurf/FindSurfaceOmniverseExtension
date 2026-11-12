"""Shared, UI-free launch planning for the standalone FindSurface demos.

The launcher extension never enables the demo implementation in its host.
Only the child Kit process receives the demo experience and payload folders.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class DemoSpec:
    launcher_id: str
    title: str
    main_extension: str
    experience: str
    runtime_kind: str
    runtime_version: str

    @classmethod
    def read(cls, launcher_root: Path) -> "DemoSpec":
        return cls(**json.loads((launcher_root / "config/demo.json").read_text(encoding="utf-8")))


@dataclass(frozen=True)
class LaunchPlan:
    command: tuple[str, ...]
    cwd: Path
    runtime_root: Path
    environment: tuple[tuple[str, str], ...] = ()


def payload_root(launcher_root: Path) -> Path:
    """Prefer a staged, self-contained payload; otherwise use the source checkout."""
    bundled = launcher_root / "data/payload"
    if bundled.is_dir():
        return bundled
    source = launcher_root.parent.parent
    if source.name == "source" and (source / "apps").is_dir():
        return source
    raise ValueError("Demo payload is missing. Prepare the launcher from the demo checkout first.")


def inspect_runtime(root: Path, spec: DemoSpec) -> tuple[Path, Path]:
    # Keep a build's kit symlink spelling: adjacent extscache belongs to that build.
    root = Path(os.path.abspath(root.expanduser()))
    if root.is_file():
        root = root.parent
    if spec.runtime_kind == "isaac":
        if root.name == "kit":
            root = root.parent
        version_file = root / "VERSION"
        version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else ""
        executable = root / "kit" / ("kit.exe" if os.name == "nt" else "kit")
    else:
        if (root / "kit").is_dir() and not (root / "kernel/config/kit-core.json").is_file():
            root = root / "kit"
        config = root / "kernel/config/kit-core.json"
        version = str(json.loads(config.read_text(encoding="utf-8")).get("crashreporter", {}).get("data", {}).get("buildVersion", "")) if config.is_file() else ""
        executable = root / ("kit.exe" if os.name == "nt" else "kit")
    match = re.match(r"(\d+\.\d+\.\d+)(?:\D|$)", version)
    if not executable.is_file() or not match or match.group(1) != spec.runtime_version:
        raise ValueError(f"Select an installed {spec.runtime_kind} {spec.runtime_version} runtime: {root}")
    return root, executable


def discover_runtime(launcher_root: Path, spec: DemoSpec, requested: str = "") -> tuple[Path, Path]:
    if requested.strip():
        return inspect_runtime(Path(requested.strip()), spec)
    candidates = []
    variable = "ISAACSIM_ROOT" if spec.runtime_kind == "isaac" else "KIT_ROOT"
    if os.environ.get(variable):
        candidates.append(Path(os.environ[variable]))
    source = payload_root(launcher_root)
    project = source.parent
    manifest = project / ".installation/manifest.json"
    if source.name == "source" and manifest.is_file():
        record = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if record.get("runtime", {}).get("path"):
            candidates.append(Path(record["runtime"]["path"]))
    if source.name == "source":
        candidates.extend([project / "kit", project / "_build" / ("windows-x86_64" if os.name == "nt" else "linux-x86_64") / "release/kit"])
    # The host is only a candidate, never an assumption about runtime compatibility.
    candidates.append(Path(sys.argv[0]).resolve().parent)
    if spec.runtime_kind == "isaac":
        candidates.extend([Path(f"C:/isaacsim-{spec.runtime_version}"), Path("C:/isaacsim")] if os.name == "nt" else [Path.home() / "isaacsim"])
    for candidate in candidates:
        try:
            return inspect_runtime(candidate, spec)
        except (OSError, ValueError):
            continue
    raise ValueError(f"{spec.title} requires an installed {spec.runtime_kind} {spec.runtime_version}. Enter its runtime folder below.")


def make_launch_plan(launcher_root: Path, requested: str = "", extra_args=()) -> LaunchPlan:
    launcher_root = Path(launcher_root).resolve()
    spec = DemoSpec.read(launcher_root)
    payload = payload_root(launcher_root)
    experience = payload / "apps" / spec.experience
    extensions = payload / "extensions"
    for item in (experience, extensions / spec.main_extension / "config/extension.toml", extensions / "com.findsurface.bootstrap/config/extension.toml"):
        if not item.is_file():
            raise ValueError(f"Required demo payload file is missing: {item}")
    root, executable = discover_runtime(launcher_root, spec, requested)
    command = [str(executable), str(experience)]
    folders = [extensions]
    if spec.runtime_kind == "isaac":
        folders.extend(root / name for name in ("apps", "exts", "extscache", "extsUser", "extsDeprecated"))
    else:
        folders.append(root.parent / "extscache")
    for folder in folders:
        if folder.is_dir():
            command.extend(["--ext-folder", str(folder)])
    sdk = local_sdk(payload)
    environment = ()
    if sdk is not None:
        environment = (("FINDSURFACE_APP_SDK_PATH", str(sdk)),)
        if spec.runtime_kind == "isaac":
            command.append(f"--/exts/{spec.main_extension}/findSurfaceLibraryPath={sdk}")
    command.extend(str(arg) for arg in extra_args)
    return LaunchPlan(tuple(command), root, root, environment)


def local_sdk(payload: Path) -> Path | None:
    platform = "windows-x86_64" if os.name == "nt" else "linux-x86_64"
    filename = "FindSurface.dll" if os.name == "nt" else "libFindSurface.so"
    sdk = payload / "extensions/com.findsurface.bootstrap/data/native" / platform / filename
    # Match Start_Demo's explicitly recorded private/external SDK selection.
    manifest = payload.parent / ".installation/manifest.json"
    if payload.name == "source" and manifest.is_file():
        record = json.loads(manifest.read_text(encoding="utf-8-sig"))
        recorded = record.get("sdk", {}).get("path")
        if recorded and Path(recorded).is_file():
            return Path(recorded)
    return sdk if sdk.is_file() else None


class DemoProcess:
    """Track this launcher's child; disabling the launcher leaves the demo running."""
    def __init__(self):
        self.process = None

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self, plan: LaunchPlan):
        if self.running:
            raise ValueError("This launcher already has a running demo. Close it before starting another.")
        environment = os.environ.copy()
        # Let the selected Kit runtime initialize its own Python environment.
        for key in ("PYTHONHOME", "PYTHONPATH"):
            environment.pop(key, None)
        # Do not inherit another demo's SDK override from the host process.
        environment.pop("FINDSURFACE_APP_SDK_PATH", None)
        environment.update(plan.environment)
        self.process = subprocess.Popen(list(plan.command), cwd=str(plan.cwd), env=environment,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return self.process


def stage_launcher(project: Path, launcher_id: str, destination: Path) -> Path:
    """Create a local launchable folder, without publishing or modifying the checkout.

    The app definition is copied from source/apps each time, avoiding a second
    maintained copy. A fresh destination is required to avoid stale payload files.
    """
    project, destination = Path(project).resolve(), Path(destination).resolve()
    source = project / "source/extensions" / launcher_id
    spec = DemoSpec.read(source)
    if destination.exists():
        raise ValueError(f"Choose a fresh staging destination: {destination}")
    if destination == project or project.is_relative_to(destination) or destination.is_relative_to(project / "source"):
        raise ValueError("Staging destination must not overlap the source tree.")
    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache", "*.pdb", "*.lib", "*.exp")
    shutil.copytree(source, destination, ignore=ignore)
    payload = destination / "data/payload"
    (payload / "apps").mkdir(parents=True)
    shutil.copy2(project / "source/apps" / spec.experience, payload / "apps" / spec.experience)
    for name in (spec.main_extension, "com.findsurface.bootstrap"):
        shutil.copytree(project / "source/extensions" / name, payload / "extensions" / name, ignore=ignore)
    sdk = local_sdk(project / "source")
    if sdk is not None:
        platform = "windows-x86_64" if os.name == "nt" else "linux-x86_64"
        filename = "FindSurface.dll" if os.name == "nt" else "libFindSurface.so"
        target = payload / "extensions/com.findsurface.bootstrap/data/native" / platform / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        if sdk.resolve() != target.resolve():
            shutil.copy2(sdk, target)
    return destination
