#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import platform
import sys
import urllib.request
from pathlib import Path


DEFAULT_ASSET_PATHS = {
    "windows-x86_64": Path("data/native/windows-x86_64/FindSurface.dll"),
    "linux-x86_64": Path("data/native/linux-x86_64/libFindSurface.so"),
}
DEFAULT_RELEASE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "sdk_release.json"


class SdkAcquisitionError(RuntimeError):
    pass


def platform_asset_key(system=None, machine=None):
    system_name = (system or platform.system()).lower()
    machine_name = (machine or platform.machine()).lower()
    if machine_name in {"amd64", "x64"}:
        machine_name = "x86_64"
    if system_name == "windows":
        return f"windows-{machine_name}"
    if system_name == "linux":
        return f"linux-{machine_name}"
    raise SdkAcquisitionError(f"Unsupported FindSurface SDK platform: {system or platform.system()}")


def load_release_config(path=DEFAULT_RELEASE_CONFIG_PATH):
    config_path = Path(path)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SdkAcquisitionError(f"FindSurface SDK release config could not be read: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise SdkAcquisitionError(f"FindSurface SDK release config is invalid JSON: {exc}") from exc
    if not isinstance(config, dict):
        raise SdkAcquisitionError("FindSurface SDK release config must be a JSON object.")
    if not config.get("release_base_url"):
        raise SdkAcquisitionError("FindSurface SDK release config must include release_base_url.")
    if not config.get("release_tag"):
        raise SdkAcquisitionError("FindSurface SDK release config must include release_tag.")
    if not isinstance(config.get("assets"), dict):
        raise SdkAcquisitionError("FindSurface SDK release config must include an assets object.")
    return config


def acquire_sdk_release_asset(
    extension_root,
    asset_key=None,
    release_config=None,
    release_config_path=DEFAULT_RELEASE_CONFIG_PATH,
    sha256=None,
    fetcher=None,
    dry_run=False,
):
    key = asset_key or platform_asset_key()
    config = release_config or load_release_config(release_config_path)
    name = config["assets"].get(key)
    if not name:
        raise SdkAcquisitionError(f"FindSurface SDK release config has no asset for {key}.")

    base_url = str(config["release_base_url"]).rstrip("/")
    tag = str(config["release_tag"]).strip()
    url = f"{base_url}/{tag}/{name}"
    output_path = Path(extension_root) / DEFAULT_ASSET_PATHS[key]

    payload = (fetcher or _fetch_bytes)(url)
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if sha256 and actual_sha256.lower() != str(sha256).lower():
        raise SdkAcquisitionError(
            f"FindSurface SDK checksum mismatch for {key}: expected {sha256}, got {actual_sha256}."
        )

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)

    return {
        "version": tag,
        "asset_key": key,
        "url": url,
        "path": output_path,
        "sha256": actual_sha256,
        "dry_run": dry_run,
    }


def _fetch_bytes(url):
    with urllib.request.urlopen(_request(url)) as response:
        return response.read()


def _request(url):
    headers = {}
    active_token = os.environ.get("FINDSURFACE_SDK_TOKEN")
    if active_token:
        scheme = os.environ.get("FINDSURFACE_SDK_AUTH_SCHEME", "Bearer").strip() or "Bearer"
        headers["Authorization"] = f"{scheme} {active_token}"
    return urllib.request.Request(url, headers=headers)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch the FindSurface native SDK binary from the release config.")
    parser.add_argument("--asset-key", help="Asset key to fetch, such as windows-x86_64 or linux-x86_64.")
    parser.add_argument(
        "--release-config",
        default=DEFAULT_RELEASE_CONFIG_PATH,
        type=Path,
        help="Path to config/sdk_release.json.",
    )
    parser.add_argument("--sha256", default=os.environ.get("FINDSURFACE_SDK_SHA256"), help="Optional SHA-256 checksum.")
    parser.add_argument(
        "--extension-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="FindSurfaceExtension checkout root. Defaults to this tool's repository root.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Download and verify without writing the SDK binary.")
    args = parser.parse_args(argv)

    try:
        result = acquire_sdk_release_asset(
            extension_root=args.extension_root,
            asset_key=args.asset_key,
            release_config_path=args.release_config,
            sha256=args.sha256,
            dry_run=args.dry_run,
        )
    except SdkAcquisitionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    action = "verified" if result["dry_run"] else "installed"
    print(
        f"FindSurface SDK {result['version']} {action}: "
        f"{result['asset_key']} -> {result['path']} sha256={result['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
