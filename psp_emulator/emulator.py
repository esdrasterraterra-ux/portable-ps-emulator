from __future__ import annotations


class InputController:
    """Controla o estado de botões do PSP em um nível inicial."""

    BUTTONS = {
        "up",
        "down",
        "left",
        "right",
        "cross",
        "circle",
        "square",
        "triangle",
        "l",
        "r",
        "start",
        "select",
    }

    def __init__(self):
        self.state = {button: False for button in sorted(self.BUTTONS)}

    def press(self, *buttons: str) -> None:
        for button in buttons:
            if button in self.state:
                self.state[button] = True

    def release(self, *buttons: str) -> None:
        for button in buttons:
            if button in self.state:
                self.state[button] = False

    def set_state(self, values: dict[str, bool]) -> None:
        for button, pressed in values.items():
            if button in self.state:
                self.state[button] = bool(pressed)

    def snapshot(self) -> dict[str, bool]:
        return dict(self.state)

    def is_pressed(self, button: str) -> bool:
        return bool(self.state.get(button, False))

    def clear(self) -> None:
        for button in self.state:
            self.state[button] = False


__all__ = ["InputController"]
