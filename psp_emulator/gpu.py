from __future__ import annotations


class Framebuffer:
    """Framebuffer simples para renderização 2D do PSP."""

    def __init__(self, width: int = 480, height: int = 272, background: tuple[int, int, int] = (0, 0, 0)):
        self.width = max(1, width)
        self.height = max(1, height)
        self.background = background
        self.pixels = [background for _ in range(self.width * self.height)]

    def _clamp(self, value: int, limit: int) -> int:
        return max(0, min(value, limit - 1))

    def _index(self, x: int, y: int) -> int:
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise IndexError(f"Coordenada fora do framebuffer: ({x}, {y})")
        return y * self.width + x

    def clear(self, color: tuple[int, int, int] | None = None) -> None:
        fill = color if color is not None else self.background
        self.pixels = [fill for _ in range(self.width * self.height)]

    def draw_pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[self._index(x, y)] = tuple(channel & 0xFF for channel in color)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int]) -> None:
        for py in range(max(0, y), min(self.height, y + height)):
            for px in range(max(0, x), min(self.width, x + width)):
                self.pixels[self._index(px, py)] = tuple(channel & 0xFF for channel in color)

    def draw_line(self, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            if 0 <= x1 < self.width and 0 <= y1 < self.height:
                self.draw_pixel(x1, y1, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def draw_sprite(self, x: int, y: int, sprite: list[list[tuple[int, int, int]]], transparent: tuple[int, int, int] | None = None) -> None:
        for row_index, row in enumerate(sprite):
            for col_index, color in enumerate(row):
                if transparent is not None and color == transparent:
                    continue
                self.draw_pixel(x + col_index, y + row_index, color)

    def snapshot(self) -> list[tuple[int, int, int]]:
        return list(self.pixels)

    def summary(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "background": self.background,
            "pixels": self.width * self.height,
        }


class PSPGPU:
    """GPU simplificada para produção de quadros e renderização de telas de teste."""

    def __init__(self, width: int = 480, height: int = 272, background: tuple[int, int, int] = (0, 0, 0)):
        self.framebuffer = Framebuffer(width=width, height=height, background=background)
        self.frame = 0

    def clear(self, color: tuple[int, int, int] | None = None) -> None:
        self.framebuffer.clear(color)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int]) -> None:
        self.framebuffer.fill_rect(x, y, width, height, color)

    def draw_line(self, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        self.framebuffer.draw_line(x1, y1, x2, y2, color)

    def draw_sprite(self, x: int, y: int, sprite: list[list[tuple[int, int, int]]], transparent: tuple[int, int, int] | None = None) -> None:
        self.framebuffer.draw_sprite(x, y, sprite, transparent=transparent)

    def present(self) -> dict:
        self.frame += 1
        return {"frame": self.frame, "size": (self.framebuffer.width, self.framebuffer.height)}

    def summary(self) -> dict:
        info = self.framebuffer.summary()
        info["frame"] = self.frame
        return info


__all__ = ["Framebuffer", "PSPGPU"]


path":"psp_emulator/input.py","content":"from __future__ import annotations


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


path":"tests/test_phase7.py","content":"from psp_emulator.gpu import Framebuffer, PSPGPU


def test_framebuffer_clear_and_fill():
    fb = Framebuffer(width=10, height=10, background=(0, 0, 0))
    fb.clear((10, 20, 30))
    assert fb.pixels[0] == (10, 20, 30)
    fb.fill_rect(2, 2, 3, 2, (255, 0, 0))
    assert fb.pixels[2 + 2 * 10] == (255, 0, 0)


def test_gpu_draw_sprite_and_present():
    gpu = PSPGPU(width=8, height=8)
    sprite = [
        [(255, 0, 0), (255, 0, 0)],
        [(0, 255, 0), (0, 255, 0)],
    ]
    gpu.draw_sprite(1, 1, sprite, transparent=(0, 0, 0))
    info = gpu.present()
    assert info["frame"] == 1
    assert gpu.summary()["frame"] == 1


def test_draw_line_updates_pixels():
    fb = Framebuffer(width=5, height=5)
    fb.draw_line(0, 0, 4, 4, (1, 2, 3))
    assert fb.pixels[0] == (1, 2, 3)
    assert fb.pixels[4 + 4 * 5] == (1, 2, 3)
