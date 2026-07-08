from pathlib import Path


SCHEMA_PLUGIN_NAME = "findsurfaceUsdSchemas"

GEOMETRY_EXPORT_API = "FindSurfaceGeometryExportAPI"
DETECTION_RESULT_API = "FindSurfaceDetectionResultAPI"
INLIER_POINTS_API = "FindSurfaceInlierPointsAPI"
VISUALIZATION_API = "FindSurfaceVisualizationAPI"

ROLE_GEOMETRY_EXPORT = "geometry_export"
ROLE_DETECTION_RESULT = "detection_result"
ROLE_INLIER_POINTS = "inlier_points"
ROLE_VISUALIZATION = "visualization"

_ROLE_API_SCHEMAS = {
    ROLE_GEOMETRY_EXPORT: (GEOMETRY_EXPORT_API,),
    ROLE_DETECTION_RESULT: (DETECTION_RESULT_API,),
    ROLE_INLIER_POINTS: (INLIER_POINTS_API,),
    ROLE_VISUALIZATION: (VISUALIZATION_API,),
}
_schema_plugin_registered = False


def applied_api_schemas(role):
    return _ROLE_API_SCHEMAS.get(role, ())


def api_schemas_metadata_lines(role, indent=0):
    schemas = applied_api_schemas(role)
    if not schemas:
        return []
    prefix = " " * indent
    values = ", ".join(f'"{schema}"' for schema in schemas)
    return [f"{prefix}prepend apiSchemas = [{values}]"]


def has_applied_api_schema(prim, role):
    schemas = set(applied_api_schemas(role))
    if not schemas or not prim:
        return False
    metadata = prim.GetMetadata("apiSchemas")
    if metadata is None:
        return False
    explicit = getattr(metadata, "explicitItems", None) or []
    prepended = getattr(metadata, "prependedItems", None) or []
    appended = getattr(metadata, "appendedItems", None) or []
    deleted = set(getattr(metadata, "deletedItems", None) or [])
    applied = (set(str(item) for item in explicit) | set(str(item) for item in prepended) | set(str(item) for item in appended))
    return bool((schemas - deleted) & applied)


def schema_plugin_root():
    extension_root = Path(__file__).resolve().parents[2]
    return extension_root / "data" / "usd_plugins" / SCHEMA_PLUGIN_NAME


def register_schema_plugin():
    global _schema_plugin_registered
    if _schema_plugin_registered:
        return True
    try:
        from pxr import Plug
    except ImportError:
        return False

    resources = schema_plugin_root() / "resources"
    if not resources.exists():
        return False
    Plug.Registry().RegisterPlugins(str(resources))
    _schema_plugin_registered = True
    return True
