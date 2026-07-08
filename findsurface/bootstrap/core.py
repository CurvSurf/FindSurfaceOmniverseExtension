from .native import DETECTION_TYPES, DetectionOptions, NativeFindSurfaceProvider
from .results import FindSurfaceResult


class FindSurfaceDetector:
    """Small public facade for native FindSurface detection.

    This class is intentionally independent from the app viewport, workspace,
    point-cloud import, picking, preview mesh, and Omniverse UI workflow.
    """

    def __init__(self, provider=None):
        self._provider = provider or NativeFindSurfaceProvider()

    def detect(self, points, seed_index, options=None, active_mask=None, active_generation=None):
        options = normalize_detection_options(options)
        active_mask = _normalize_active_mask(points, active_mask)
        result = self._provider.detect(
            points,
            active_mask,
            int(seed_index),
            options,
            active_generation=active_generation,
        )
        core_result = _to_core_result(result)
        if active_generation is not None:
            core_result.active_generation = int(active_generation)
        return core_result


def normalize_detection_options(options=None):
    if options is None:
        return DetectionOptions()
    if isinstance(options, DetectionOptions):
        return options
    if isinstance(options, dict):
        return DetectionOptions(**options)
    raise TypeError("options must be None, a dict, or DetectionOptions.")


def supported_detection_types():
    return DETECTION_TYPES


def _normalize_active_mask(points, active_mask):
    point_count = len(points)
    if active_mask is None:
        return [True] * point_count
    if len(active_mask) != point_count:
        raise ValueError("active_mask length must match points length.")
    # Preserve caller-provided mask identity so NativeFindSurfaceProvider can
    # reuse its prepared point-cloud cache across repeated detection calls.
    return active_mask


def _to_core_result(result):
    return FindSurfaceResult(
        id=str(getattr(result, "id", "")),
        type=str(getattr(result, "type", "")),
        seed_index=int(getattr(result, "seed_index", -1)),
        seed_position=tuple(getattr(result, "seed_position", (0.0, 0.0, 0.0))),
        inlier_indices=list(getattr(result, "inlier_indices", []) or []),
        active_generation=int(getattr(result, "active_generation", 0) or 0),
        measurement_accuracy=float(getattr(result, "measurement_accuracy", 0.0) or 0.0),
        rms_error=float(getattr(result, "rms_error", 0.0) or 0.0),
        confidence=getattr(result, "confidence", None),
        parameters=dict(getattr(result, "parameters", {}) or {}),
    )


__all__ = [
    "DETECTION_TYPES",
    "DetectionOptions",
    "FindSurfaceDetector",
    "FindSurfaceResult",
    "normalize_detection_options",
    "supported_detection_types",
]
