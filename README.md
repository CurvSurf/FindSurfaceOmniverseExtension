# FindSurface Omniverse Extension

**Curv*Surf* FindSurface™** reusable extension package for NVIDIA Omniverse Kit.

[FindSurface Main Hub](https://github.com/CurvSurf/FindSurface)

## Overview

FindSurface Omniverse Extension provides the `com.findsurface.bootstrap` Kit
extension. It is the Omniverse-side wrapper around the native FindSurface SDK:
it loads the native SDK through Python `ctypes`, exposes a small Python
detection API, and registers the FindSurface USD schema resources used by apps
that export detected geometry.

This repository intentionally does not own the demo application's point-cloud
importer, viewport, camera controls, picking UX, preview mesh generation,
workspace format, toolbar, or app windows. Those features live in the paired
FindSurface Omniverse demo app repository.

The extension currently supports these FindSurface detection types:

- Auto
- Plane
- Sphere
- Cylinder
- Cone
- Torus

It also provides an optional `omni.ui` FindSurface parameter-window utility.
Apps may choose to use that utility, or they may build their own parameter UI
and call the core detection API directly.

See [DOCUMENTATION.md](DOCUMENTATION.md) for the full API reference, usage
requirements, and examples.

## Samples

These are the samples to help you get started to make your application with the library (more samples are to be added in the future):

- [Omniverse Demo](https://github.com/CurvSurf/FindSurfaceOmniverseDemo)


## Public Python API

Core detection symbols are available from `findsurface.bootstrap` without
constructing any app UI:

```python
from findsurface.bootstrap import DetectionOptions, FindSurfaceDetector

detector = FindSurfaceDetector()
result = detector.detect(
    points=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
    seed_index=0,
    options=DetectionOptions(detection_type="Auto"),
)
```

The optional parameter-window builder is exposed lazily:

```python
from findsurface.bootstrap import FindSurfaceWindowCallbacks, build_findsurface_window
```

The caller owns models, validation, callbacks, point-cloud loading, picking, and
visualization. The utility only assembles the FindSurface parameter controls.

## How to use with the demo app

Place this repository beside the demo application checkout, or point the demo
launcher to it:

```powershell
$env:FINDSURFACE_EXTENSION_ROOT = "C:\path\to\FindSurfaceExtension"
.\tools\launch.ps1 -KitExe "C:\path\to\kit.exe"
```

Kit needs this extension folder:

```text
FindSurface_Omniverse/source/extensions
```

When this repository is used as a submodule by the demo app, it should be
checked out at:

```text
FindSurface_Omniverse/source/extensions/com.findsurface.bootstrap
```

## Native SDK libraries

The core FindSurface native SDK binaries are intentionally not tracked in Git.
For local Windows development, place the SDK DLL here:

```text
data/native/windows-x86_64/FindSurface.dll
```

For Linux distribution, the expected SDK path is:

```text
data/native/linux-x86_64/libFindSurface.so
```

Release builds should obtain these native FindSurface library binary assets from
CurvSurf's binary distribution or a binary-asset acquisition step instead of
committing them to source control. The demo repository root also includes
`NATIVE_SDK.md`, which lists the development checkout and thin-package manual
install paths.

The binary-asset acquisition helper and runtime fallback both read
`config/sdk_release.json`. Update that file when the GitHub release tag changes;
do not duplicate the release URL or tag in source code or documentation:

```powershell
python tools/fetch_findsurface_sdk.py
```

The same acquisition path is used automatically by the default SDK wrapper when
the platform native library is missing. Set `FINDSURFACE_SDK_AUTO_DOWNLOAD=0`
to disable that runtime fallback.

Point-picking helper binaries are app-owned artifacts. They should be built and
packaged by the demo app repository, not tracked in this reusable extension.

## Extension layout

```text
config/extension.toml                Kit extension metadata and dependencies.
data/native/                         Ignored native SDK binary location.
data/usd_plugins/                    Codeless USD schema plugin resources.
findsurface/bootstrap/               Core wrapper, result, schema, and utility modules.
tests/                               Extension-owned unit tests.
```

## About License

The Python portions of this repository are separate from the native FindSurface
SDK binary. The FindSurface SDK is owned by CurvSurf, Inc.; refer to CurvSurf's
FindSurface repositories and release terms for SDK licensing, platform support,
point-count limits, and commercial-use requirements.
