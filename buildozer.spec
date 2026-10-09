from __future__ import annotations

from typing import Dict, List, Tuple

try:
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.graphics import Color, Rectangle
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.widget import Widget
except Exception:  # pragma: no cover - optional dependency on Android build
    App = None
    Clock = None
    BoxLayout = object
    Button = object
    GridLayout = object
    Label = object
    Widget = object

from .emulator import PSPEmulator


class AndroidPSPPrototype:
    """Prototipo Android para emular a inicializacao do PSP e renderizar um framebuffer simples."""

    def __init__(self, rom_path: str | None = None):
        self.emulator = PSPEmulator(rom_path=rom_path)
        self.framebuffer = self.emulator.gpu.framebuffer if hasattr(self.emulator, "gpu") else None
        self.status = "booting"

    def boot(self) -> Dict[str, object]:
        self.status = "ready"
        self.emulator.boot()
        return {
            "status": self.status,
            "bios": self.emulator.bios.version,
            "message": "PSP Android prototype inicializado",
            "summary": self.emulator.state_summary(),
        }

    def run_step(self, steps: int = 1) -> Dict[str, object]:
        self.emulator.run(steps)
        return {
            "status": self.status,
            "pc": self.emulator.cpu.pc,
            "summary": self.emulator.state_summary(),
        }

    def render_status(self) -> str:
        return self.emulator.state_summary()


if App:
    class PSPScreen(Widget):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.size_hint = (None, None)
            self.width = 480
            self.height = 272
            self.canvas.before.clear()
            with self.canvas:
                Color(0.05, 0.08, 0.10, 1)
                Rectangle(pos=self.pos, size=self.size)
            self.bind(pos=self.redraw, size=self.redraw)
            self.redraw()

        def redraw(self, *args):
            self.canvas.before.clear()
            with self.canvas.before:
                Color(0.05, 0.08, 0.10, 1)
                Rectangle(pos=self.pos, size=self.size)
                Color(0.2, 0.8, 0.35, 1)
                Rectangle(pos=(self.x + 20, self.y + 20), size=(self.width - 40, self.height - 40))
                Color(1, 1, 1, 1)

    class PSPAndroidApp(App):
        title = "PSP Android Prototype"

        def build(self):
            self.prototype = AndroidPSPPrototype()
            self.root = BoxLayout(orientation="vertical", spacing=10, padding=10)

            self.screen = PSPScreen()
            self.root.add_widget(self.screen)

            info = Label(text="PSP prototype em modo inicialização")
            self.root.add_widget(info)

            buttons = GridLayout(cols=3, size_hint_y=None, height=180, spacing=8)
            for label in ["↑", "↓", "←", "→", "X", "O", "Start", "Select", "Home"]:
                btn = Button(text=label)
                btn.bind(on_press=self.on_button_press)
                buttons.add_widget(btn)
            self.root.add_widget(buttons)

            self.boot_timer = Clock.schedule_interval(self.tick, 1.0 / 10.0)
            return self.root

        def on_button_press(self, instance):
            text = str(instance.text)
            if text == "Home":
                self.prototype.boot()
            elif text in {"Start", "Select"}:
                self.prototype.run_step(2)
            else:
                self.prototype.run_step(1)
            self.root.children[1].text = self.prototype.render_status()

        def tick(self, dt):
            self.prototype.run_step(1)
            self.root.children[1].text = self.prototype.render_status()

        def on_stop(self):
            if hasattr(self, "boot_timer"):
                self.boot_timer.cancel()


    def main():
        PSPAndroidApp().run()
else:
    def main():
        prototype = AndroidPSPPrototype()
        print("PSP Android prototype carregado em modo texto.")
        print(prototype.boot())
        print(prototype.run_step(5))


if __name__ == "__main__":
    main()
