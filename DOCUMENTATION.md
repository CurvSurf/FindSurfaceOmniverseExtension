# FindSurfaceExtension Documentation

This document describes how to use the reusable `FindSurfaceExtension`
repository independently from the FindSurface Omniverse demo app.

The extension package is `com.findsurface.bootstrap`. It provides:

- A Python facade over the native FindSurface SDK.
- Result dataclasses and geometry parameter conversion helpers.
- Optional `omni.ui` controls for FindSurface parameters.
- Codeless USD schema resources for FindSurface geometry export metadata.

It does not provide the demo app's point-cloud importer, viewport, camera,
picking UX, workspace format, toolbar, preview rendering, or export workflow.
Applications should own those pieces and call this extension for detection and
shared schema support.

## Repository Layout

```text
FindSurfaceExtension/
  config/extension.toml
  data/native/
    windows-x86_64/FindSurface.dll
    linux-x86_64/libFindSurface.so
  data/usd_plugins/findsurfaceUsdSchemas/
  findsurface/bootstrap/
    core.py
    native.py
    results.py
    usd_schema.py
    findsurface_window.py
    findsurface_sdk/
  tests/
  tools/fetch_findsurface_sdk.py
```

## Kit Extension Setup

Add this extension folder to the Kit launch command:

```text
the parent directory containing this checkout
```

Then enable or depend on the Kit extension:

```toml
[dependencies]
"com.findsurface.bootstrap" = {}
```

The package metadata lives in:

```text
config/extension.toml
```

When the Kit extension starts, it attempts to register the bundled USD schema
plugin resources. If the USD Python modules are unavailable, detection can
still be used, but schema registration returns `False`.

## Native SDK Library

`FindSurfaceDetector` uses `NativeFindSurfaceProvider`, which constructs
`FindSurfaceSdk()` by default. The SDK wrapper searches for a platform-specific
native library under the extension repository root:

```text
Windows: data/native/windows-x86_64/FindSurface.dll
Linux:   data/native/linux-x86_64/libFindSurface.so
```

You can use an explicit native library path at the low-level wrapper layer:

```python
from findsurface.bootstrap.findsurface_sdk import FindSurfaceSdk
from findsurface.bootstrap.native import NativeFindSurfaceProvider
from findsurface.bootstrap import FindSurfaceDetector

sdk = FindSurfaceSdk(library_path=r"C:\path\to\FindSurface.dll")
provider = NativeFindSurfaceProvider(sdk=sdk)
detector = FindSurfaceDetector(provider=provider)
```

The native binaries are not tracked in source control. Use CurvSurf's SDK
distribution or the acquisition helper:

```powershell
python tools\fetch_findsurface_sdk.py
```

The helper and default SDK wrapper read `config/sdk_release.json`. Update that
file when the release tag changes. If automatic download fails, install the
binary manually at the path shown above. In a thin package, the same files
belong under:

```text
Windows: exts/com.findsurface.bootstrap/data/native/windows-x86_64/FindSurface.dll
Linux:   exts/com.findsurface.bootstrap/data/native/linux-x86_64/libFindSurface.so
```

## Public Python API

Import the core API from `findsurface.bootstrap`:

```python
from findsurface.bootstrap import (
    DETECTION_TYPES,
    DetectionOptions,
    FindSurfaceDetector,
    FindSurfaceResult,
    normalize_detection_options,
    supported_detection_types,
)
```

Available detection type names:

```python
("Auto", "Plane", "Sphere", "Cylinder", "Cone", "Torus")
```

`supported_detection_types()` returns the same tuple as `DETECTION_TYPES`.

### DetectionOptions

`DetectionOptions` is a frozen dataclass used to configure one detection call.

```python
from findsurface.bootstrap import DetectionOptions

options = DetectionOptions(
    detection_type="Auto",
    seed_radius=1.0,
    measurement_accuracy=0.02,
    mean_distance=0.05,
    radial_expansion=5,
    lateral_extension=5,
)
```

Fields:

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `detection_type` | `str` | `"Auto"` | One of `Auto`, `Plane`, `Sphere`, `Cylinder`, `Cone`, `Torus`. |
| `seed_radius` | `float` | `1.0` | Must be greater than `0`. |
| `measurement_accuracy` | `float` | `0.02` | Must be greater than `0`. |
| `mean_distance` | `float` | `0.05` | Must be greater than `0`. |
| `radial_expansion` | `int` | `5` | Must be from `0` to `10`. |
| `lateral_extension` | `int` | `5` | Must be from `0` to `10`. |

`normalize_detection_options()` accepts `None`, a `DetectionOptions` instance,
or a dictionary:

```python
options = normalize_detection_options({
    "detection_type": "Sphere",
    "measurement_accuracy": 0.004,
})
```

Invalid option object types raise `TypeError`. Invalid field values are
reported by `DetectionOptions.validate()` during native detection.

### FindSurfaceDetector

`FindSurfaceDetector` is the main app-facing facade.

```python
from findsurface.bootstrap import DetectionOptions, FindSurfaceDetector

points = [
    (0.0, 0.0, 0.0),
    (1.0, 0.0, 0.0),
    (2.0, 0.0, 0.0),
]

detector = FindSurfaceDetector()
result = detector.detect(
    points=points,
    seed_index=0,
    options=DetectionOptions(detection_type="Auto"),
)
```

Signature:

```python
FindSurfaceDetector.detect(
    points,
    seed_index,
    options=None,
    active_mask=None,
    active_generation=None,
)
```

Arguments:

| Argument | Meaning |
| --- | --- |
| `points` | Sequence of `(x, y, z)` numeric coordinates. |
| `seed_index` | Index into `points` used as the seed point. |
| `options` | `None`, `dict`, or `DetectionOptions`. |
| `active_mask` | Optional boolean list with the same length as `points`; inactive points are excluded. |
| `active_generation` | Optional integer cache/version token for repeated calls with the same active point set. |

Behavior:

- If `active_mask` is omitted, all points are active.
- If `active_mask` is supplied, its length must match `points`.
- The seed point must be inside the point array and active.
- The native provider currently rejects inputs above `200,000` points.
- `active_generation` is copied to the returned result and is also used by the
  native provider to reuse prepared point-cloud buffers when possible.

Example with an active mask:

```python
active_mask = [True, False, True]

result = detector.detect(
    points=points,
    seed_index=0,
    options={"detection_type": "Sphere", "measurement_accuracy": 0.004},
    active_mask=active_mask,
    active_generation=3,
)
```

### FindSurfaceResult

Detection returns a `FindSurfaceResult` dataclass:

```python
from findsurface.bootstrap import FindSurfaceResult
```

Fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | `str` | Generated id such as `Plane_001`. |
| `type` | `str` | Result type: `Plane`, `Sphere`, `Cylinder`, `Cone`, or `Torus`. |
| `seed_index` | `int` | Original index of the seed point. |
| `seed_position` | `tuple[float, float, float]` | Seed coordinate. |
| `inlier_indices` | `list[int]` | Original point indices classified as inliers. |
| `active_generation` | `int` | Active-set generation associated with the result. |
| `measurement_accuracy` | `float` | Measurement accuracy used for detection. |
| `rms_error` | `float` | Native FindSurface RMS error. |
| `confidence` | `float | None` | Reserved optional confidence value. |
| `parameters` | `dict[str, Any]` | Geometry-specific parameters. |

Result `parameters` are normalized by result type:

| Type | Parameter keys |
| --- | --- |
| `Plane` | `origin`, `x_axis`, `y_axis`, `z_axis`, `width`, `height`, `upper_left`, `upper_right`, `lower_left`, `lower_right` |
| `Sphere` | `center`, `origin`, `radius` |
| `Cylinder` | `origin`, `x_axis`, `y_axis`, `z_axis`, `height`, `bottom`, `top`, `radius` |
| `Cone` | `origin`, `x_axis`, `y_axis`, `z_axis`, `height`, `bottom`, `top`, `bottom_radius`, `top_radius` |
| `Torus` | `origin`, `x_axis`, `y_axis`, `z_axis`, `center`, `axis`, `major_radius`, `tube_radius`, `start_tube_center`, `sweep_angle` |

The axes are intended as a stable transform frame for app-side visualization or
export. The extension does not create meshes or viewport objects by itself.

## Errors and Validation

Relevant exception classes:

```python
from findsurface.bootstrap.native import (
    FindSurfaceError,
    ValidationError,
)
from findsurface.bootstrap.findsurface_sdk import FindSurfaceSdkError
```

Common failure cases:

- Missing native library: `FileNotFoundError`.
- Automatic native library download failure: the underlying network, HTTP, or
  file error is propagated by the wrapper. Demo apps should catch this and show
  a user-facing setup message.
- Unsupported platform in `default_library_path()`: `RuntimeError`.
- Invalid detection options: `ValidationError`.
- Active mask length mismatch: `ValueError`.
- Seed index outside the point cloud: `ValueError`.
- Seed point inactive: `ValueError`.
- Point count above `200,000`: `FindSurfaceError`.
- Native SDK returns an invalid or empty result: `FindSurfaceSdkError`.

## Low-Level Native API

Most apps should use `FindSurfaceDetector`. The lower-level API is available for
testing, custom library loading, or advanced integrations:

```python
from findsurface.bootstrap.native import NativeFindSurfaceProvider
from findsurface.bootstrap.findsurface_sdk import FindSurfaceSdk
from findsurface.bootstrap.findsurface_sdk.constants import (
    FsBoolParameter,
    FsFeatureType,
    FsFloatParameter,
    FsIntParameter,
)
```

`FindSurfaceSdk` wraps the native `ctypes` ABI:

- `create_context()`
- `release_context(context)`
- `set_float(context, parameter, value)`
- `set_int(context, parameter, value)`
- `set_boolean(context, parameter, value)`
- `get_boolean(context, parameter)`
- `build_pointcloud_buffer(points)`
- `set_pointcloud(context, points)`
- `set_pointcloud_buffer(context, point_array, point_count)`
- `find(context, feature_type)`
- `get_outlier_flags(context, point_count)`

The wrapper binds these native functions:

- `fs_create_context`
- `fs_release_context`
- `fs_set_float`
- `fs_set_int`
- `fs_set_boolean`
- `fs_get_boolean`
- `fs_set_pointcloud`
- `fs_find_surface`
- `fs_find_plane`
- `fs_find_sphere`
- `fs_find_cylinder`
- `fs_find_cone`
- `fs_find_torus`
- `fs_get_outlier_flags`

Use the high-level facade unless your app needs direct control over native SDK
contexts.

## USD Schema Helpers

The extension includes codeless USD schema plugin resources under:

```text
data/usd_plugins/findsurfaceUsdSchemas
```

Import the helper module:

```python
from findsurface.bootstrap import usd_schema
```

Important constants:

```python
usd_schema.ROLE_GEOMETRY_EXPORT
usd_schema.ROLE_DETECTION_RESULT
usd_schema.ROLE_INLIER_POINTS
usd_schema.ROLE_VISUALIZATION
```

Role-to-API-schema mapping:

| Role | API schema |
| --- | --- |
| `geometry_export` | `FindSurfaceGeometryExportAPI` |
| `detection_result` | `FindSurfaceDetectionResultAPI` |
| `inlier_points` | `FindSurfaceInlierPointsAPI` |
| `visualization` | `FindSurfaceVisualizationAPI` |

Helpers:

```python
usd_schema.register_schema_plugin()
usd_schema.schema_plugin_root()
usd_schema.applied_api_schemas(usd_schema.ROLE_DETECTION_RESULT)
usd_schema.api_schemas_metadata_lines(usd_schema.ROLE_GEOMETRY_EXPORT, indent=4)
usd_schema.has_applied_api_schema(prim, usd_schema.ROLE_VISUALIZATION)
```

`api_schemas_metadata_lines()` is useful when writing USDA text manually:

```python
lines = usd_schema.api_schemas_metadata_lines(
    usd_schema.ROLE_GEOMETRY_EXPORT,
    indent=4,
)
# ['    prepend apiSchemas = ["FindSurfaceGeometryExportAPI"]']
```

When working inside Kit or another USD-enabled Python runtime, call
`register_schema_plugin()` before relying on these schemas being discoverable.

## Optional FindSurface Parameter Window

The extension provides an optional `omni.ui` parameter-window builder. It is
loaded lazily because it requires Omniverse Kit Python modules.

```python
from findsurface.bootstrap import (
    FindSurfaceWindowCallbacks,
    FindSurfaceWindowModels,
    build_findsurface_window,
)
```

Model keys required by `FindSurfaceWindowModels.from_mapping()`:

- `lateral_extension`
- `radial_expansion`

Callback functions required by `FindSurfaceWindowCallbacks`:

- `range_float_row(label, parameter_name, framed=False)`
- `int_slider_row(label, model, minimum, maximum, name, framed=False)`
- `build_parameter_pad_row()`

Example:

```python
callbacks = FindSurfaceWindowCallbacks(
    range_float_row=build_range_row,
    int_slider_row=build_int_slider_row,
    build_parameter_pad_row=build_parameter_pad_row,
)

models = FindSurfaceWindowModels.from_mapping({
    "lateral_extension": lateral_extension_model,
    "radial_expansion": radial_expansion_model,
})

build_findsurface_window(models, callbacks)
```

The builder assembles controls for:

- `measurement_accuracy`
- `mean_distance`
- `seed_radius`
- `lateral_extension`
- `radial_expansion`

It does not perform validation, trigger detection, load point clouds, own
application state, or render detection results.

## Minimal App Integration Pattern

1. Check out this repository under a Kit extension folder, for example
   `source/extensions/com.findsurface.bootstrap`.
2. Add a dependency on `com.findsurface.bootstrap`.
3. Ensure the native SDK library exists at the expected path or inject a custom
   `FindSurfaceSdk`.
4. Let your app load or generate point coordinates.
5. Let your app choose a seed index and optional active mask.
6. Call `FindSurfaceDetector.detect()`.
7. Use `FindSurfaceResult.inlier_indices` and `FindSurfaceResult.parameters` to
   build your own visualization, capture flow, workspace, or USD export.
8. Register and apply the USD schema helpers when writing FindSurface metadata.

Minimal detection example:

```python
from findsurface.bootstrap import DetectionOptions, FindSurfaceDetector

detector = FindSurfaceDetector()

result = detector.detect(
    points=my_points,
    seed_index=my_seed_index,
    options=DetectionOptions(
        detection_type="Cylinder",
        seed_radius=0.15,
        measurement_accuracy=0.003,
        mean_distance=0.05,
        radial_expansion=5,
        lateral_extension=5,
    ),
    active_mask=my_active_mask,
    active_generation=my_active_generation,
)

print(result.type)
print(result.inlier_indices)
print(result.parameters)
```

## Test Command

Run the extension-owned unit tests from `FindSurfaceExtension/`:

```powershell
python -m unittest discover tests
```

The tests cover the core API, native wrapper signatures, result conversion,
USD schema helpers, SDK acquisition helper behavior, and optional UI builder
structure.
