from .core import (
    DETECTION_TYPES,
    DetectionOptions,
    FindSurfaceDetector,
    FindSurfaceResult,
    normalize_detection_options,
    supported_detection_types,
)

def __getattr__(name):
    if name == "FindSurfaceBootstrapExtension":
        try:
            from .bootstrap_extension import FindSurfaceBootstrapExtension as extension_class
        except ModuleNotFoundError as exc:
            raise RuntimeError("FindSurfaceBootstrapExtension requires Omniverse Kit Python modules.") from exc
        return extension_class
    if name == "BorderedGroupView":
        try:
            from .ui_views import BorderedGroupView as group_view
        except ModuleNotFoundError as exc:
            raise RuntimeError("BorderedGroupView requires Omniverse Kit Python modules.") from exc
        return group_view
    if name == "FindSurfaceWindowCallbacks":
        try:
            from .findsurface_window import FindSurfaceWindowCallbacks as callbacks_class
        except ModuleNotFoundError as exc:
            raise RuntimeError("FindSurfaceWindowCallbacks requires Omniverse Kit Python modules.") from exc
        return callbacks_class
    if name == "FindSurfaceWindowModels":
        try:
            from .findsurface_window import FindSurfaceWindowModels as models_class
        except ModuleNotFoundError as exc:
            raise RuntimeError("FindSurfaceWindowModels requires Omniverse Kit Python modules.") from exc
        return models_class
    if name == "build_findsurface_window":
        try:
            from .findsurface_window import build_findsurface_window as builder
        except ModuleNotFoundError as exc:
            raise RuntimeError("build_findsurface_window requires Omniverse Kit Python modules.") from exc
        return builder
    raise AttributeError(name)

__all__ = [
    "DETECTION_TYPES",
    "DetectionOptions",
    "FindSurfaceDetector",
    "FindSurfaceResult",
    "FindSurfaceBootstrapExtension",
    "BorderedGroupView",
    "FindSurfaceWindowCallbacks",
    "FindSurfaceWindowModels",
    "build_findsurface_window",
    "normalize_detection_options",
    "supported_detection_types",
]
