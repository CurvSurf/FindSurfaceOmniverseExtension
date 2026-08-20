import sys
import types
import unittest
from pathlib import Path


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXTENSION_ROOT))


from findsurface.bootstrap import (  # noqa: E402
    DETECTION_TYPES,
    DetectionOptions,
    FindSurfaceDetector,
    FindSurfaceResult,
    normalize_detection_options,
    supported_detection_types,
)


class FakeProvider:
    def __init__(self):
        self.calls = []
        self.close_calls = 0

    def detect(self, points, active_mask, seed_index, options, active_generation=None):
        self.calls.append(
            {
                "points": points,
                "active_mask": active_mask,
                "seed_index": seed_index,
                "options": options,
                "active_generation": active_generation,
            }
        )
        return types.SimpleNamespace(
            id="Plane_001",
            type="Plane",
            seed_index=seed_index,
            seed_position=tuple(points[seed_index]),
            inlier_indices=[0, seed_index],
            measurement_accuracy=options.measurement_accuracy,
            rms_error=0.001,
            confidence=None,
            parameters={"origin": (0.0, 0.0, 0.0)},
        )

    def close(self):
        self.close_calls += 1


class CoreApiTests(unittest.TestCase):
    def test_package_import_exposes_core_without_omniverse_modules(self):
        self.assertIn("Plane", DETECTION_TYPES)
        self.assertEqual(supported_detection_types(), DETECTION_TYPES)

    def test_detector_normalizes_defaults_and_returns_core_result(self):
        provider = FakeProvider()
        detector = FindSurfaceDetector(provider=provider)
        points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]

        result = detector.detect(points, seed_index=1, active_generation=7)

        self.assertIsInstance(result, FindSurfaceResult)
        self.assertEqual(result.type, "Plane")
        self.assertEqual(result.seed_index, 1)
        self.assertEqual(result.seed_position, (1.0, 0.0, 0.0))
        self.assertEqual(result.active_generation, 7)
        self.assertEqual(provider.calls[0]["active_mask"], [True, True])
        self.assertEqual(provider.calls[0]["active_generation"], 7)

    def test_detector_accepts_option_dict_and_preserves_active_mask_identity(self):
        provider = FakeProvider()
        detector = FindSurfaceDetector(provider=provider)
        points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
        active_mask = [True, False]

        detector.detect(
            points,
            seed_index=0,
            options={"detection_type": "Sphere", "measurement_accuracy": 0.004},
            active_mask=active_mask,
        )

        call = provider.calls[0]
        self.assertIs(call["active_mask"], active_mask)
        self.assertIsInstance(call["options"], DetectionOptions)
        self.assertEqual(call["options"].detection_type, "Sphere")
        self.assertAlmostEqual(call["options"].measurement_accuracy, 0.004)

    def test_detector_rejects_mask_length_mismatch(self):
        detector = FindSurfaceDetector(provider=FakeProvider())
        with self.assertRaises(ValueError):
            detector.detect([(0.0, 0.0, 0.0)], seed_index=0, active_mask=[True, False])

    def test_detector_closes_provider_once_and_rejects_later_detection(self):
        provider = FakeProvider()
        detector = FindSurfaceDetector(provider=provider)

        detector.close()
        detector.close()

        self.assertEqual(provider.close_calls, 1)
        with self.assertRaisesRegex(RuntimeError, "closed"):
            detector.detect([(0.0, 0.0, 0.0)], seed_index=0)

    def test_normalize_detection_options_rejects_unknown_type(self):
        with self.assertRaises(TypeError):
            normalize_detection_options(object())


if __name__ == "__main__":
    unittest.main()
