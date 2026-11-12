"""Optional Kit UI for the shared standalone demo launcher."""
from pathlib import Path

import omni.ui as ui

from .demo_launcher import DemoProcess, DemoSpec, discover_runtime, make_launch_plan


class DemoLauncherWindow:
    def __init__(self, launcher_root):
        self.root = Path(launcher_root).resolve()
        self.spec = DemoSpec.read(self.root)
        self.child = DemoProcess()
        self.window = ui.Window(f"{self.spec.title} Launcher", width=620, height=320)
        with self.window.frame:
            with ui.VStack(spacing=8, style={"margin": 12}):
                ui.Label(self.spec.title, height=25)
                ui.Label("Open the standalone demo in a separate application.", word_wrap=True, height=30)
                ui.Button("Run Demo", height=30, clicked_fn=self.launch)
                ui.Label(f"Runtime folder ({self.spec.runtime_kind} {self.spec.runtime_version})", height=20)
                self.runtime = ui.SimpleStringModel("")
                ui.StringField(self.runtime, height=24)
                self.status = ui.Label("", word_wrap=True, height=40)
        try:
            root, _ = discover_runtime(self.root, self.spec)
            self.runtime.set_value(str(root))
            self.status.text = "Ready. The demo starts only when you click Run Demo."
        except (OSError, ValueError) as error:
            self.status.text = str(error)

    def launch(self):
        try:
            plan = make_launch_plan(self.root, self.runtime.as_string)
            process = self.child.start(plan)
            self.status.text = f"Demo started (PID {process.pid}). Close the demo to run it again."
        except (OSError, ValueError) as error:
            self.status.text = str(error)

    def close(self):
        # The child is independent of the host and remains open.
        self.window.destroy()
        self.window = None
