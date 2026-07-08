from dataclasses import dataclass, field
from typing import Any


@dataclass
class FindSurfaceResult:
    id: str
    type: str
    seed_position: tuple[float, float, float]
    seed_index: int = -1
    inlier_indices: list[int] = field(default_factory=list)
    active_generation: int = 0
    measurement_accuracy: float = 0.0
    rms_error: float = 0.0
    confidence: float | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


__all__ = ["FindSurfaceResult"]
