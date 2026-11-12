# FindSurface Omniverse Core

Reusable detection API and USD schema resources. Enabling this extension does
not start a demo. Version 1.1.0 also provides the shared demo launcher backend
and optional launcher window.

Requirements: Kit 110.1.2 / Python 3.12, Windows and Linux x86-64 (tested), including
Isaac Sim 6.0.1. No Kit/Isaac Sim runtime is included. Other Kit versions are
not advertised. Platform-specific archives include native SDK v1.0.1 with
its pinned SHA-256 checksum. The two launchers require core 1.1.0 exactly.

API: `from findsurface.bootstrap import FindSurfaceDetector, DetectionOptions`

Full documentation: https://github.com/CurvSurf/FindSurfaceOmniverseExtension/blob/main/DOCUMENTATION.md

Retain THIRD_PARTY_NOTICES.md. The SDK is subject to separate CurvSurf SDK
terms and applicable commercial agreements; this package grants no additional
SDK rights. See https://github.com/CurvSurf/FindSurface and the SDK release at
https://github.com/CurvSurf/FindSurfaceOmniverseExtension/releases/tag/v1.0.1.
Community packages are not supported or endorsed by NVIDIA.
Support: https://github.com/CurvSurf/FindSurfaceOmniverseExtension/issues
