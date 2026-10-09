from __future__ import annotations


class Framebuffer:
    """Framebuffer simplificado para renderização do PSP."""

    def __init__(self, width: int = 480, height: int = 272, background: tuple[int, int, int] = (0, 0, 0)):
        self.width = width
        self.height = height
        self.background = background
        self.pixels = [[background for _ in range(width)] for _ in range(height)]

    def clear(self, color: tuple[int, int, int] | None = None) -> None:
        color = color or self.background
        self.pixels = [[color for _ in range(self.width)] for _ in range(self.height)]

    def draw_pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = color

    def fill_rect(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int]) -> None:
        for py in range(y, min(y + height, self.height)):
            for px in range(x, min(x + width, self.width)):
                self.pixels[py][px] = color

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        return self.pixels[y][x]

    def summary(self) -> dict:
        return {"width": self.width, "height": self.height, "pixels": self.width * self.height}


class PSPGPU:
    """GPU emulada com suporte inicial a framebuffer e desenho simples."""

    def __init__(self, width: int = 480, height: int = 272):
        self.framebuffer = Framebuffer(width=width, height=height)
        self.frame_count = 0

    def clear(self, color: tuple[int, int, int] | None = None) -> None:
        self.framebuffer.clear(color)

    def draw_pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        self.framebuffer.draw_pixel(x, y, color)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int]) -> None:
        self.framebuffer.fill_rect(x, y, width, height, color)

    def present(self) -> dict:
        self.frame_count += 1
        return {"frame": self.frame_count, "resolution": (self.framebuffer.width, self.framebuffer.height)}

    def summary(self) -> dict:
        return {"frame_count": self.frame_count, **self.framebuffer.summary()}


__all__ = ["Framebuffer", "PSPGPU"]
