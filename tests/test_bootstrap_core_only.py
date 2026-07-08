import importlib.util
import sys
import types
import unittest
from pathlib import Path


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_ROOT = EXTENSION_ROOT / "findsurface" / "bootstrap"


def install_omni_stubs(core_only=True):
    class Settings:
        def get_as_bool(self, path):
            return bool(core_only and path == "/findsurface/bootstrap/coreOnly")

        def get(self, path):
            return None

    carb = types.ModuleType("carb")
    carb.settings = types.SimpleNamespace(get_settings=lambda: Settings())
    carb.log_error = lambda message: None
    carb.log_warn = lambda message: None
    carb.log_info = lambda message: None
    carb_input = types.ModuleType("carb.input")
    carb_input.KEYBOARD_MODIFIER_FLAG_CONTROL = 1
    carb_input.KEYBOARD_MODIFIER_FLAG_SHIFT = 2
    carb_input.KEYBOARD_MODIFIER_FLAG_ALT = 4
    carb.input = carb_input

    omni = types.ModuleType("omni")
    ext = types.ModuleType("omni.ext")
    ext.IExt = object
    kit = types.ModuleType("omni.kit")
    actions = types.ModuleType("omni.kit.actions")
    actions_core = types.ModuleType("omni.kit.actions.core")
    app = types.ModuleType("omni.kit.app")
    menu = types.ModuleType("omni.kit.menu")
    menu_utils = types.ModuleType("omni.kit.menu.utils")
    window = types.ModuleType("omni.kit.window")
    filepicker = types.ModuleType("omni.kit.window.filepicker")
    appwindow = types.ModuleType("omni.appwindow")
    ui = types.ModuleType("omni.ui")
    scene = types.ModuleType("omni.ui.scene")

    class AbstractManipulatorModel:
        def __init__(self):
            pass

        def get_item(self, name):
            return name

        def _item_changed(self, item):
            pass

    class Manipulator:
        def __init__(self):
            pass

        def invalidate(self):
            pass

    actions_core.get_action_registry = lambda: types.SimpleNamespace()
    app.get_app = lambda: types.SimpleNamespace()
    app.GLOBAL_EVENT_POST_QUIT = "omni.kit.app:post_quit"
    app.GLOBAL_EVENT_PRE_SHUTDOWN = "omni.kit.app:pre_shutdown"
    menu_utils.MenuItemDescription = lambda *args, **kwargs: types.SimpleNamespace()
    menu_utils.add_menu_items = lambda *args, **kwargs: None
    menu_utils.remove_menu_items = lambda *args, **kwargs: None
    filepicker.FilePickerDialog = object
    appwindow.get_default_app_window = lambda: None
    scene.AbstractManipulatorModel = AbstractManipulatorModel
    scene.Manipulator = Manipulator
    scene.AspectRatioPolicy = types.SimpleNamespace(STRETCH=0)
    scene.SceneView = object
    scene.Points = lambda *args, **kwargs: None
    curve = lambda *args, **kwargs: None
    curve.CurveType = types.SimpleNamespace(LINEAR=0)
    scene.Curve = curve
    scene.PolygonMesh = lambda *args, **kwargs: None
    scene.Line = lambda *args, **kwargs: None
    ui.scene = scene

    omni.ext = ext
    omni.kit = kit
    omni.appwindow = appwindow
    omni.ui = ui
    kit.actions = actions
    kit.app = app
    kit.menu = menu
    kit.window = window
    actions.core = actions_core
    menu.utils = menu_utils
    window.filepicker = filepicker

    for name, module in {
        "carb": carb,
        "carb.input": carb_input,
        "omni": omni,
        "omni.ext": ext,
        "omni.kit": kit,
        "omni.kit.actions": actions,
        "omni.kit.actions.core": actions_core,
        "omni.kit.app": app,
        "omni.kit.menu": menu,
        "omni.kit.menu.utils": menu_utils,
        "omni.kit.window": window,
        "omni.kit.window.filepicker": filepicker,
        "omni.appwindow": appwindow,
        "omni.ui": ui,
        "omni.ui.scene": scene,
    }.items():
        sys.modules[name] = module


def load_extension_module():
    pkg = types.ModuleType("findsurface")
    pkg.__path__ = [str(BOOTSTRAP_ROOT.parent)]
    bootstrap_pkg = types.ModuleType("findsurface.bootstrap")
    bootstrap_pkg.__path__ = [str(BOOTSTRAP_ROOT)]
    sdk_pkg = types.ModuleType("findsurface.bootstrap.findsurface_sdk")
    sdk_pkg.__path__ = [str(BOOTSTRAP_ROOT / "findsurface_sdk")]
    sys.modules["findsurface"] = pkg
    sys.modules["findsurface.bootstrap"] = bootstrap_pkg
    sys.modules["findsurface.bootstrap.findsurface_sdk"] = sdk_pkg

    spec = importlib.util.spec_from_file_location("findsurface.bootstrap.extension", BOOTSTRAP_ROOT / "extension.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_bootstrap_startup_module():
    pkg = types.ModuleType("findsurface")
    pkg.__path__ = [str(BOOTSTRAP_ROOT.parent)]
    bootstrap_pkg = types.ModuleType("findsurface.bootstrap")
    bootstrap_pkg.__path__ = [str(BOOTSTRAP_ROOT)]
    sys.modules["findsurface"] = pkg
    sys.modules["findsurface.bootstrap"] = bootstrap_pkg

    spec = importlib.util.spec_from_file_location(
        "findsurface.bootstrap.bootstrap_extension",
        BOOTSTRAP_ROOT / "bootstrap_extension.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BootstrapCoreOnlyTests(unittest.TestCase):
    def test_legacy_extension_module_registers_schema_without_constructing_app_ui(self):
        install_omni_stubs(core_only=True)
        extension_module = load_extension_module()
        extension = extension_module.FindSurfaceBootstrapExtension()
        calls = []
        extension._register_usd_schema_plugin = lambda: calls.append("schema")

        extension.on_startup("com.findsurface.bootstrap")
        extension.on_shutdown()

        self.assertEqual(calls, ["schema"])
        self.assertFalse(hasattr(extension, "_viewport"))

    def test_bootstrap_startup_module_registers_schema_only(self):
        install_omni_stubs(core_only=False)
        extension_module = load_bootstrap_startup_module()
        extension = extension_module.FindSurfaceBootstrapExtension()
        calls = []
        extension._register_usd_schema_plugin = lambda: calls.append("schema")

        extension.on_startup("com.findsurface.bootstrap")
        extension.on_shutdown()

        self.assertEqual(calls, ["schema"])
        self.assertFalse(hasattr(extension, "_viewport"))


if __name__ == "__main__":
    unittest.main()
