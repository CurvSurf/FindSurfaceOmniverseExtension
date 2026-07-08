from dataclasses import dataclass

import omni.ui as ui

from .ui_views import BorderedGroupView


@dataclass(frozen=True)
class FindSurfaceWindowModels:
    auto_detect: object
    lateral_extension: object
    radial_expansion: object

    @classmethod
    def from_mapping(cls, models):
        return cls(
            auto_detect=models["auto_detect"],
            lateral_extension=models["lateral_extension"],
            radial_expansion=models["radial_expansion"],
        )


class FindSurfaceWindowCallbacks:
    def __init__(
        self,
        range_float_row,
        int_slider_row,
        build_parameter_pad_row,
    ):
        self.range_float_row = range_float_row
        self.int_slider_row = int_slider_row
        self.build_parameter_pad_row = build_parameter_pad_row


def build_findsurface_window(models, callbacks):
    """Build the optional FindSurface parameter window UI.

    The caller owns models, validation, callbacks, and detection behavior. This
    utility only assembles the FindSurface-specific parameter controls.
    """

    window_models = _normalize_window_models(models)

    with ui.VStack(spacing=8):
        ui.Spacer(height=8)
        with ui.HStack(height=26, spacing=6):
            ui.CheckBox(model=window_models.auto_detect, width=22)
            ui.Label("Enable Hover Preview")
        ui.Spacer(height=2)
        with BorderedGroupView("Measurement Parameters", row_heights=(76, 76)):
            callbacks.range_float_row("Accuracy", "measurement_accuracy", framed=False)
            callbacks.range_float_row("Mean Distance", "mean_distance", framed=False)
        with BorderedGroupView("Object Size", row_heights=(76,)):
            callbacks.range_float_row("Seed Radius", "seed_radius", framed=False)
        with BorderedGroupView("Region Growing", row_heights=(30, 30)):
            callbacks.int_slider_row(
                "Lateral Extension",
                window_models.lateral_extension,
                minimum=0,
                maximum=10,
                name="lateral_extension",
                framed=False,
            )
            callbacks.int_slider_row(
                "Radial Expansion",
                window_models.radial_expansion,
                minimum=0,
                maximum=10,
                name="radial_expansion",
                framed=False,
            )
        callbacks.build_parameter_pad_row()
        ui.Spacer()


def _normalize_window_models(models):
    if isinstance(models, FindSurfaceWindowModels):
        return models
    return FindSurfaceWindowModels.from_mapping(models)


__all__ = ["FindSurfaceWindowCallbacks", "FindSurfaceWindowModels", "build_findsurface_window"]
