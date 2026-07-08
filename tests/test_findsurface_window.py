import sys
import types
import unittest
from pathlib import Path


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXTENSION_ROOT))


class UiContext:
    def __init__(self, events=None, name=None):
        self._events = events
        self._name = name

    def __enter__(self):
        if self._events is not None and self._name:
            self._events.append(("enter", self._name))
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._events is not None and self._name:
            self._events.append(("exit", self._name))
        return False


def install_ui_stubs(events):
    omni = sys.modules.setdefault("omni", types.ModuleType("omni"))
    ui = types.ModuleType("omni.ui")
    ui.VStack = lambda **kwargs: UiContext(events, "VStack")
    ui.HStack = lambda **kwargs: UiContext(events, "HStack")
    ui.Spacer = lambda **kwargs: events.append(("Spacer", dict(kwargs)))
    ui.CheckBox = lambda **kwargs: events.append(("CheckBox", dict(kwargs)))

    def label(text, **kwargs):
        widget = types.SimpleNamespace(text=text, kwargs=dict(kwargs))
        events.append(("Label", text, dict(kwargs), widget))
        return widget

    ui.Label = label
    omni.ui = ui
    sys.modules["omni.ui"] = ui


class FakeBorderedGroupView:
    def __init__(self, title, row_heights=None):
        self.title = title
        self.row_heights = row_heights

    def __enter__(self):
        EVENTS.append(("group", self.title, self.row_heights))
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


EVENTS = []


install_ui_stubs(EVENTS)
import findsurface.bootstrap as bootstrap  # noqa: E402
from findsurface.bootstrap import findsurface_window  # noqa: E402


findsurface_window.BorderedGroupView = FakeBorderedGroupView


class FindSurfaceWindowTests(unittest.TestCase):
    def setUp(self):
        EVENTS.clear()

    def test_build_findsurface_window_delegates_app_owned_controls(self):
        calls = []
        auto_detect = object()
        lateral_extension = object()
        radial_expansion = object()

        callbacks = findsurface_window.FindSurfaceWindowCallbacks(
            range_float_row=lambda *args, **kwargs: calls.append(("range", args, kwargs)),
            int_slider_row=lambda *args, **kwargs: calls.append(("int", args, kwargs)),
            build_parameter_pad_row=lambda: calls.append(("pad", (), {})),
        )
        models = findsurface_window.FindSurfaceWindowModels(
            auto_detect=auto_detect,
            lateral_extension=lateral_extension,
            radial_expansion=radial_expansion,
        )

        findsurface_window.build_findsurface_window(models, callbacks)

        self.assertIn(("group", "Measurement Parameters", (76, 76)), EVENTS)
        self.assertIn(("group", "Object Size", (76,)), EVENTS)
        self.assertIn(("group", "Region Growing", (30, 30)), EVENTS)
        self.assertEqual(calls[0], ("range", ("Accuracy", "measurement_accuracy"), {"framed": False}))
        self.assertEqual(calls[1], ("range", ("Mean Distance", "mean_distance"), {"framed": False}))
        self.assertEqual(calls[2], ("range", ("Seed Radius", "seed_radius"), {"framed": False}))
        self.assertEqual(calls[3][0], "int")
        self.assertEqual(calls[3][1][0], "Lateral Extension")
        self.assertIs(calls[3][1][1], lateral_extension)
        self.assertEqual(calls[3][2]["name"], "lateral_extension")
        self.assertEqual(calls[4][0], "int")
        self.assertEqual(calls[4][1][0], "Radial Expansion")
        self.assertIs(calls[4][1][1], radial_expansion)
        self.assertEqual(calls[4][2]["name"], "radial_expansion")
        self.assertEqual(calls[-1][0], "pad")
        checkboxes = [event for event in EVENTS if event[0] == "CheckBox"]
        self.assertEqual(len(checkboxes), 1)
        self.assertIs(checkboxes[0][1]["model"], auto_detect)

    def test_build_findsurface_window_accepts_legacy_mapping_models(self):
        calls = []
        callbacks = findsurface_window.FindSurfaceWindowCallbacks(
            range_float_row=lambda *args, **kwargs: calls.append(("range", args, kwargs)),
            int_slider_row=lambda *args, **kwargs: calls.append(("int", args, kwargs)),
            build_parameter_pad_row=lambda: calls.append(("pad", (), {})),
        )

        findsurface_window.build_findsurface_window(
            {
                "auto_detect": object(),
                "lateral_extension": object(),
                "radial_expansion": object(),
            },
            callbacks,
        )

        self.assertEqual(calls[0][0], "range")
        self.assertEqual(calls[-1][0], "pad")

    def test_package_lazily_exports_optional_window_utility(self):
        self.assertIs(bootstrap.FindSurfaceWindowCallbacks, findsurface_window.FindSurfaceWindowCallbacks)
        self.assertIs(bootstrap.FindSurfaceWindowModels, findsurface_window.FindSurfaceWindowModels)
        self.assertIs(bootstrap.build_findsurface_window, findsurface_window.build_findsurface_window)


if __name__ == "__main__":
    unittest.main()
