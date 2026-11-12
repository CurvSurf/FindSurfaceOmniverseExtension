"""Build and verify Community Release archives locally. No publishing operations."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import sys
import tomllib
import zipfile


CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))
from findsurface.bootstrap.demo_launcher import DemoSpec, stage_launcher

PLATFORMS = ("windows-x86_64", "linux-x86_64")
EXCLUDE = {".git", ".agents", ".codex", ".aws", ".installation", ".artifacts",
           "__pycache__", ".pytest_cache", "tests", "tools", "premake5.lua",
           ".gitattributes", ".gitignore", "community_release.json"}
EXCLUDE_SUFFIXES = {".pyc", ".pdb", ".lib", ".exp", ".a", ".log"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_config(root):
    return json.loads((root / "community_release.json").read_text(encoding="utf-8"))


def clean_tree(root, platform):
    for item in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if item.name in EXCLUDE or item.name in (set(PLATFORMS) - {platform}) or item.suffix in EXCLUDE_SUFFIXES:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()


def narrow_target(root, platform):
    config = root / "config/extension.toml"
    text = config.read_text(encoding="utf-8")
    text, count = re.subn(r'^platform\s*=\s*\[.*\]$', f'platform = ["{platform}"]', text, flags=re.M)
    if count != 1:
        raise ValueError(f"Expected one platform target: {config}")
    config.write_text(text, encoding="utf-8", newline="\n")


def verify_extension(root, expected_id=None):
    config = tomllib.loads((root / "config/extension.toml").read_text(encoding="utf-8"))
    package = config["package"]
    if expected_id is not None and package.get("name") != expected_id:
        raise ValueError("Extension ID and directory do not match")
    for field in ("name", "title", "description", "version", "repository", "authors", "keywords"):
        if not package.get(field):
            raise ValueError(f"Missing package.{field}: {root}")
    if package["name"].startswith("omni") or not re.fullmatch(r"\d+\.\d+\.\d+", package["version"]):
        raise ValueError(f"Invalid extension name/version: {root}")
    if not package["repository"].startswith("https://github.com/CurvSurf/"):
        raise ValueError("Expected the public CurvSurf repository URL")
    for field in ("readme", "changelog", "icon", "preview_image"):
        relative = PurePosixPath(package[field])
        if relative.is_absolute() or ".." in relative.parts or not (root / str(relative)).is_file():
            raise ValueError(f"Missing/unsafe package.{field}: {root}")
    if package["version"] not in (root / package["changelog"]).read_text(encoding="utf-8"):
        raise ValueError("Current version is absent from changelog")
    return config


def verify_native(path, platform):
    if not path.is_file():
        raise ValueError(f"Required native library is missing: {path}")
    data = path.read_bytes()
    if platform == "windows-x86_64":
        if data[:2] != b"MZ" or len(data) < 64:
            raise ValueError(f"Not a PE library: {path}")
        offset = struct.unpack_from("<I", data, 60)[0]
        if data[offset:offset + 4] != b"PE\0\0" or struct.unpack_from("<H", data, offset + 4)[0] != 0x8664:
            raise ValueError(f"Not a Windows x86-64 library: {path}")
    elif data[:5] != b"\x7fELF\x02" or struct.unpack_from("<H", data, 18)[0] != 62:
        raise ValueError(f"Not a Linux x86-64 library: {path}")


def verify_sdk(core, platform):
    policy = json.loads((core / "config/sdk_release.json").read_text(encoding="utf-8"))
    sdk = core / "data/native" / platform / policy["assets"][platform]
    verify_native(sdk, platform)
    if digest(sdk) != policy["sha256"][platform]:
        raise ValueError(f"SDK checksum does not match pinned release: {sdk}")
    return {"release": policy["release_tag"], "sha256": digest(sdk)}


def verify_tree(stage, config, platform):
    extensions = stage / "exts"
    names = sorted(p.name for p in extensions.iterdir() if p.is_dir())
    if names != [config["extension_id"]]:
        raise ValueError(f"Unexpected top-level registry extensions: {names}")
    extension = extensions / config["extension_id"]
    metadata = verify_extension(extension, config["extension_id"])
    expected_category = "other" if config["kind"] == "core" else "example"
    if metadata["package"]["category"] != expected_category:
        raise ValueError(f"Expected category {expected_category}: {extension}")
    target = metadata["package"]["target"]
    if target["platform"] != [platform] or target["kit"] != [config["kit_version"]]:
        raise ValueError("Package target is not restricted to the prepared platform and Kit version")
    if config["kind"] == "core":
        sdk = verify_sdk(extension, platform)
    else:
        spec = DemoSpec.read(extension)
        dependencies = metadata.get("dependencies", {})
        core_dependency = dependencies.get("com.findsurface.bootstrap", {})
        if spec.main_extension in dependencies or core_dependency != {"version": "1.1.0", "exact": True}:
            raise ValueError("Launcher must require core 1.1.0 without enabling the demo in the host")
        payload = extension / "data/payload"
        core = payload / "extensions/com.findsurface.bootstrap"
        core_metadata = verify_extension(core, "com.findsurface.bootstrap")
        if core_metadata["package"]["version"] != core_dependency["version"]:
            raise ValueError("Payload core version differs from the host dependency")
        # Kit permits its appended generated version-lock table to reopen a
        # table. Standard TOML does not; parse the authored dependency section.
        app_text = (payload / "apps" / spec.experience).read_text(encoding="utf-8")
        app = tomllib.loads(app_text.split("# BEGIN GENERATED PART", 1)[0])
        if spec.main_extension not in app.get("dependencies", {}):
            raise ValueError("Demo experience does not enable its implementation")
        main = payload / "extensions" / spec.main_extension
        if not (main / "config/extension.toml").is_file():
            raise ValueError("Demo implementation is missing")
        main_metadata = tomllib.loads((main / "config/extension.toml").read_text(encoding="utf-8"))
        if main_metadata["package"]["category"] != "example" or main_metadata["package"]["target"]["platform"] != [platform]:
            raise ValueError("Bundled demo category/platform differs from its release")
        verify_native(main / "data/native" / platform / config["picker"][platform], platform)
        sdk = verify_sdk(core, platform)
    for item in stage.rglob("*"):
        if item.name in EXCLUDE or item.suffix in EXCLUDE_SUFFIXES:
            raise ValueError(f"Development artifact in archive: {item}")
        if item.name in (set(PLATFORMS) - {platform}):
            raise ValueError("Another platform's binaries are included")
    return {"extension": config["extension_id"], "version": metadata["package"]["version"], "sdk": sdk}


def prepare(project, output, platform):
    config = read_config(project)
    if platform not in PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}")
    if platform not in config.get("supported_platforms", ["windows-x86_64"]):
        raise ValueError(f"Platform is not approved in community_release.json: {platform}")
    if not re.fullmatch(r"v\d+\.\d+\.\d+", config["release_tag"]):
        raise ValueError("Expected a vMAJOR.MINOR.PATCH release tag")
    output = output.resolve()
    if output.exists():
        raise ValueError("Use a fresh output directory; existing results are never overwritten")
    if (output == project or project.is_relative_to(output)
            or (output.is_relative_to(project) and output.relative_to(project).parts[0] not in {".artifacts", "dist"})):
        raise ValueError("Output overlaps the source tree")
    output.mkdir(parents=True)
    stage = output / "stage"
    target = stage / "exts" / config["extension_id"]
    if config["kind"] == "core":
        ignore = shutil.ignore_patterns(*EXCLUDE, ".artifacts", "dist", "build", "*.pyc", "*.pdb", "*.lib", "*.a", "*.log")
        shutil.copytree(project, target, ignore=ignore)
        # Developer-only preparation config is not needed at runtime.
    else:
        stage_launcher(project, config["extension_id"], target)
        for filename in ("LICENSE", "THIRD_PARTY_NOTICES.md", "PRODUCT_TERMS_OMNIVERSE"):
            if (project / filename).is_file():
                shutil.copy2(project / filename, target / "docs" / filename)
    clean_tree(stage, platform)
    narrow_target(target, platform)
    if config["kind"] == "launcher":
        narrow_target(target / "data/payload/extensions/com.findsurface.bootstrap", platform)
        narrow_target(target / "data/payload/extensions" / DemoSpec.read(target).main_extension, platform)
    result = verify_tree(stage, config, platform)
    name = config["repository"].replace("/", "-") + f"-{platform}-{config['release_tag']}.zip"
    archive = output / name
    entries = {}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for item in sorted(stage.rglob("*")):
            if not item.is_file():
                continue
            relative = item.relative_to(stage).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, item.read_bytes())
            entries[relative] = digest(item)
    result.update(repository=config["repository"], release_tag=config["release_tag"], platform=platform,
                  archive=name, archive_sha256=digest(archive), files=entries, published=False)
    (output / "release-manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "release-config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    verify_archive(output)
    return archive


def verify_archive(output):
    manifest = json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))
    config = json.loads((output / "release-config.json").read_text(encoding="utf-8"))
    archive = output / manifest["archive"]
    if digest(archive) != manifest["archive_sha256"]:
        raise ValueError("Archive checksum mismatch")
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        if len(names) != len(set(names)) or set(names) != set(manifest["files"]):
            raise ValueError("Archive members differ from manifest")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or path.parts[0] != "exts":
                raise ValueError("Unsafe archive member")
            if hashlib.sha256(zipped.read(name)).hexdigest() != manifest["files"][name]:
                raise ValueError(f"Member checksum mismatch: {name}")
    # The staged tree must match the exact archive that was validated.
    actual = {p.relative_to(output / "stage").as_posix(): digest(p) for p in (output / "stage").rglob("*") if p.is_file()}
    if actual != manifest["files"]:
        raise ValueError("Staged files differ from archive")
    return verify_tree(output / "stage", config, manifest["platform"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--platform", choices=PLATFORMS, default="windows-x86_64" if sys.platform == "win32" else "linux-x86_64")
    parser.add_argument("--verify", type=Path, help="verify an existing output directory without building")
    args = parser.parse_args()
    try:
        if args.verify:
            print(json.dumps(verify_archive(args.verify.resolve()), indent=2))
        elif args.output_dir:
            print(prepare(args.project_root.resolve(), args.output_dir, args.platform))
        else:
            parser.error("Supply --output-dir or --verify")
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"ERROR: {error}\n")


if __name__ == "__main__":
    main()
