import carb
import omni.ext

from . import usd_schema


class FindSurfaceBootstrapExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._ext_id = ext_id
        self._register_usd_schema_plugin()

    def on_shutdown(self):
        pass

    def _register_usd_schema_plugin(self):
        try:
            if usd_schema.register_schema_plugin():
                carb.log_info("Registered FindSurface USD schema plugin.")
            else:
                carb.log_warn("FindSurface USD schema plugin was not registered; exports will keep fallback attributes.")
        except Exception as exc:
            carb.log_warn(f"FindSurface USD schema plugin registration failed: {exc}")


__all__ = ["FindSurfaceBootstrapExtension"]
