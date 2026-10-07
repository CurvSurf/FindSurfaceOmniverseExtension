import sys
import types
import unittest
from math import cos, pi, radians, sin
from pathlib import Path


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXTENSION_ROOT))


from findsurface.bootstrap.findsurface_sdk.constants import FsFeatureType  # noqa: E402
from findsurface.bootstrap.native import (  # noqa: E402
    DetectionOptions,
    FindSurfaceError,
    NativeFindSurfaceProvider,
    ValidationError,
    convert_raw_result,
)
from findsurface.bootstrap.results import FindSurfaceResult  # noqa: E402


class FakeSdk:
    def __init__(self):
        self.float_parameters = []
        self.int_parameters = []
        self.bool_parameters = []
        self.created_contexts = []
        self.released_contexts = []

    def create_context(self):
        context = f"ctx-{len(self.created_contexts) + 1}"
        self.created_contexts.append(context)
        return context

    def release_context(self, context):
        self.released_contexts.append(context)

    def set_float(self, context, parameter, value):
        self.float_parameters.append((context, parameter, value))

    def set_int(self, context, parameter, value):
        self.int_parameters.append((context, parameter, value))

    def set_boolean(self, context, parameter, value):
        self.bool_parameters.append((context, parameter, value))

    def build_pointcloud_buffer(self, points):
        return list(points), len(points)

    def set_pointcloud_buffer(self, context, point_array, point_count):
        return point_array

    def find(self, context, feature_type):
        self.feature_type = feature_type
        return types.SimpleNamespace(
            result_type=int(FsFeatureType.SPHERE),
            rms_error=0.125,
            sphere_result=types.SimpleNamespace(center=(1.0, 2.0, 3.0), radius=4.5),
        )

    def get_outlier_flags(self, context, point_count):
        return [0, 1, 0][:point_count]


class NativeDetectionTests(unittest.TestCase):
    def test_torus_sweep_closes_only_above_355_degrees(self):
        raw = types.SimpleNamespace(torus_result=types.SimpleNamespace(
            center=(2.0, 3.0, 4.0), axis=(0.0, 0.0, 1.0),
            mean_radius=2.0, tube_radius=0.25))
        for degrees in (270.0, 300.0, 354.999, 355.0, 355.001, 359.0):
            with self.subTest(degrees=degrees):
                half = radians(degrees / 2.0)
                # Center samples prevent the independent mean-length <0.1 rule.
                points = [(2.0 + 2.0 * cos(a), 3.0 + 2.0 * sin(a), 4.0)
                          for a in (-half, half, *([0.0] * 10))]
                original = list(points)
                result = convert_raw_result(raw, "Torus", points)
                expected = 2.0 * pi if degrees > 355.0 else radians(degrees)
                self.assertAlmostEqual(result["sweep_angle"], expected, places=12)
                self.assertEqual(result["center"], raw.torus_result.center)
                self.assertEqual(result["axis"], raw.torus_result.axis)
                self.assertEqual(result["major_radius"], 2.0)
                self.assertEqual(result["tube_radius"], 0.25)
                self.assertEqual(points, original)

    def test_torus_balanced_directions_still_produce_full_sweep(self):
        from findsurface.bootstrap.findsurface_sdk.geometry import calculate_elbow_joint
        points = [(cos(a), sin(a), 0.0) for a in (0.0, pi / 2.0, pi, 1.5 * pi)]
        _, sweep = calculate_elbow_joint(points, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 1.0)
        self.assertEqual(sweep, 2.0 * pi)

    def assertTupleAlmostEqual(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for actual_value, expected_value in zip(actual, expected):
            self.assertAlmostEqual(actual_value, expected_value)

    def test_options_validate_rejects_invalid_ranges(self):
        with self.assertRaises(ValidationError):
            DetectionOptions(detection_type="Box").validate()
        with self.assertRaises(ValidationError):
            DetectionOptions(seed_radius=0.0).validate()
        with self.assertRaises(ValidationError):
            DetectionOptions(radial_expansion=11).validate()

    def test_convert_raw_result_converts_sphere_parameters(self):
        raw_result = types.SimpleNamespace(
            sphere_result=types.SimpleNamespace(center=(1.0, 2.0, 3.0), radius=4.5)
        )

        parameters = convert_raw_result(raw_result, "Sphere", [])

        self.assertEqual(parameters["center"], (1.0, 2.0, 3.0))
        self.assertEqual(parameters["origin"], (1.0, 2.0, 3.0))
        self.assertAlmostEqual(parameters["radius"], 4.5)

    def test_convert_raw_result_converts_plane_parameters(self):
        raw_result = types.SimpleNamespace(
            plane_result=types.SimpleNamespace(
                upper_left=(-1.0, 1.0, 0.0),
                upper_right=(1.0, 1.0, 0.0),
                lower_left=(-1.0, -1.0, 0.0),
                lower_right=(1.0, -1.0, 0.0),
            )
        )

        parameters = convert_raw_result(raw_result, "Plane", [])

        self.assertEqual(parameters["upper_left"], (-1.0, 1.0, 0.0))
        self.assertEqual(parameters["upper_right"], (1.0, 1.0, 0.0))
        self.assertEqual(parameters["lower_left"], (-1.0, -1.0, 0.0))
        self.assertEqual(parameters["lower_right"], (1.0, -1.0, 0.0))
        self.assertTupleAlmostEqual(parameters["origin"], (0.0, 0.0, 0.0))
        self.assertTupleAlmostEqual(parameters["x_axis"], (1.0, 0.0, 0.0))
        self.assertTupleAlmostEqual(parameters["y_axis"], (0.0, -1.0, 0.0))
        self.assertTupleAlmostEqual(parameters["z_axis"], (0.0, 0.0, -1.0))
        self.assertAlmostEqual(parameters["width"], 2.0)
        self.assertAlmostEqual(parameters["height"], 2.0)

    def test_convert_raw_result_converts_cylinder_parameters(self):
        raw_result = types.SimpleNamespace(
            cylinder_result=types.SimpleNamespace(
                bottom=(0.0, 0.0, 0.0),
                top=(0.0, 2.0, 0.0),
                radius=0.75,
            )
        )

        parameters = convert_raw_result(raw_result, "Cylinder", [])

        self.assertEqual(parameters["bottom"], (0.0, 0.0, 0.0))
        self.assertEqual(parameters["top"], (0.0, 2.0, 0.0))
        self.assertTupleAlmostEqual(parameters["origin"], (0.0, 1.0, 0.0))
        self.assertTupleAlmostEqual(parameters["y_axis"], (0.0, 1.0, 0.0))
        self.assertAlmostEqual(parameters["height"], 2.0)
        self.assertAlmostEqual(parameters["radius"], 0.75)

    def test_convert_raw_result_converts_cone_parameters(self):
        raw_result = types.SimpleNamespace(
            cone_result=types.SimpleNamespace(
                bottom=(0.0, 0.0, 0.0),
                top=(0.0, 3.0, 0.0),
                bottom_radius=1.25,
                top_radius=0.25,
            )
        )

        parameters = convert_raw_result(raw_result, "Cone", [])

        self.assertEqual(parameters["bottom"], (0.0, 0.0, 0.0))
        self.assertEqual(parameters["top"], (0.0, 3.0, 0.0))
        self.assertTupleAlmostEqual(parameters["origin"], (0.0, 1.5, 0.0))
        self.assertTupleAlmostEqual(parameters["y_axis"], (0.0, 1.0, 0.0))
        self.assertAlmostEqual(parameters["height"], 3.0)
        self.assertAlmostEqual(parameters["bottom_radius"], 1.25)
        self.assertAlmostEqual(parameters["top_radius"], 0.25)

    def test_convert_raw_result_converts_torus_parameters(self):
        raw_result = types.SimpleNamespace(
            torus_result=types.SimpleNamespace(
                center=(0.0, 0.0, 0.0),
                axis=(0.0, 0.0, 1.0),
                mean_radius=2.0,
                tube_radius=0.25,
            )
        )

        parameters = convert_raw_result(raw_result, "Torus", [])

        self.assertEqual(parameters["center"], (0.0, 0.0, 0.0))
        self.assertEqual(parameters["axis"], (0.0, 0.0, 1.0))
        self.assertTupleAlmostEqual(parameters["origin"], (0.0, 0.0, 0.0))
        self.assertTupleAlmostEqual(parameters["z_axis"], (0.0, 0.0, 1.0))
        self.assertTupleAlmostEqual(parameters["start_tube_center"], (2.0, 0.0, 0.0))
        self.assertAlmostEqual(parameters["major_radius"], 2.0)
        self.assertAlmostEqual(parameters["tube_radius"], 0.25)
        self.assertAlmostEqual(parameters["sweep_angle"], 2.0 * pi)

    def test_provider_reuses_context_until_closed(self):
        sdk = FakeSdk()
        provider = NativeFindSurfaceProvider(sdk=sdk)
        points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)]

        first_result = provider.detect(
            points,
            [True, True, True],
            0,
            DetectionOptions(detection_type="Sphere", measurement_accuracy=0.004),
            active_generation=9,
        )
        second_result = provider.detect(
            points,
            [True, True, True],
            0,
            DetectionOptions(detection_type="Sphere", measurement_accuracy=0.004),
            active_generation=10,
        )

        self.assertIsInstance(first_result, FindSurfaceResult)
        self.assertEqual(first_result.id, "Sphere_001")
        self.assertEqual(first_result.inlier_indices, [0, 2])
        self.assertEqual(first_result.active_generation, 9)
        self.assertAlmostEqual(first_result.measurement_accuracy, 0.004)
        self.assertEqual(second_result.id, "Sphere_002")
        self.assertEqual(sdk.created_contexts, ["ctx-1"])
        self.assertEqual(sdk.released_contexts, [])

        provider.close()
        provider.close()

        self.assertEqual(sdk.released_contexts, ["ctx-1"])
        with self.assertRaisesRegex(FindSurfaceError, "closed"):
            provider.detect(
                points,
                [True, True, True],
                0,
                DetectionOptions(detection_type="Sphere"),
            )


if __name__ == "__main__":
    unittest.main()
