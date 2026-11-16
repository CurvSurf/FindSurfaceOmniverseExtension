# FindSurface Omniverse Core

Reusable detection API and USD schema resources. Enabling this extension does
not start a demo. Version 1.1.1 also provides the shared demo launcher backend
and optional launcher window.

Requirements: Kit 110.1.2 / Python 3.12, Windows and Linux x86-64 (tested), including
Isaac Sim 6.0.1. No Kit/Isaac Sim runtime is included. Other Kit versions are
not advertised. Native SDK v1.0.1 is downloaded on first use and verified
against its pinned SHA-256 checksum. The two launchers require core 1.1.1 exactly.

API: `from findsurface.bootstrap import FindSurfaceDetector, DetectionOptions`

Full documentation: https://github.com/CurvSurf/FindSurfaceOmniverseExtension/blob/main/DOCUMENTATION.md

Retain THIRD_PARTY_NOTICES.md. The SDK is subject to separate CurvSurf SDK
terms and applicable commercial agreements; this package grants no additional
SDK rights. See https://github.com/CurvSurf/FindSurface and the SDK release at
https://github.com/CurvSurf/FindSurfaceOmniverseExtension/releases/tag/v1.0.1.
Community packages are not supported or endorsed by NVIDIA.
Support: https://github.com/CurvSurf/FindSurfaceOmniverseExtension/issues

## Registry SDK delivery

Registry ZIPs exclude FindSurface.dll and libFindSurface.so. Both direct core
users and Extension Manager installations use the same default SDK wrapper:
first SDK use downloads the version and asset pinned in config/sdk_release.json,
verifies SHA-256, and saves it under data/native/<platform>. Existing files are
reused without downloading. Activation alone only registers USD schemas.
An explicit SDK path bypasses automatic acquisition; FINDSURFACE_SDK_AUTO_DOWNLOAD=0
disables it. The initial acquisition needs network access and write access to the
extension data directory. Picker binaries are independent app-owned build artifacts.
