"""PyGame interface for PSP emulator visualization and interaction."""

from __future__ import annotations

import sys
from typing import Optional

try:
    import pygame
except ImportError:
    print("PyGame not installed. Install it with: pip install pygame")
    sys.exit(1)

from .emulator import PSPEmulator


class PSPEmulatorUI:
    """PyGame-based user interface for PSP emulator."""

    # PSP Screen dimensions
    SCREEN_WIDTH = 480
    SCREEN_HEIGHT = 272
    
    # Scale factor for window (PSP screen is small)
    SCALE = 2
    
    # Colors
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (128, 128, 128)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)

    def __init__(self, rom_path: Optional[str] = None, scale: int = 2):
        """
        Initialize the PyGame UI for PSP emulator.
        
        Args:
            rom_path: Optional path to PSP ROM file
            scale: Screen scale factor (default: 2x)
        """
        pygame.init()
        
        self.rom_path = rom_path
        self.scale = scale
        self.running = True
        
        # Create window
        self.window_width = self.SCREEN_WIDTH * scale
        self.window_height = self.SCREEN_HEIGHT * scale
        self.screen = pygame.display.set_mode(
            (self.window_width, self.window_height),
            pygame.RESIZABLE
        )
        pygame.display.set_caption("PSP Emulator - Pygame UI")
        
        # Initialize emulator
        self.emulator = PSPEmulator(rom_path=rom_path)
        
        # Clock for FPS control
        self.clock = pygame.time.Clock()
        self.fps = 60  # PSP runs at 60 FPS
        
        # Font for UI text
        self.font_small = pygame.font.Font(None, 24)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_large = pygame.font.Font(None, 48)
        
        # Statistics
        self.frame_count = 0
        self.show_debug = False

    def handle_events(self) -> bool:
        """
        Handle pygame events and input.
        
        Returns:
            False if quit event received, True otherwise
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)
            
            elif event.type == pygame.KEYUP:
                self._handle_keyup(event)
            
            elif event.type == pygame.VIDEORESIZE:
                self.window_width, self.window_height = event.size
                self.screen = pygame.display.set_mode(
                    (self.window_width, self.window_height),
                    pygame.RESIZABLE
                )
        
        return True

    def _handle_keydown(self, event: pygame.event.EventType) -> None:
        """Handle key press events and map to PSP buttons."""
        key_map = {
            pygame.K_UP: "up",
            pygame.K_DOWN: "down",
            pygame.K_LEFT: "left",
            pygame.K_RIGHT: "right",
            pygame.K_z: "cross",
            pygame.K_x: "circle",
            pygame.K_c: "square",
            pygame.K_v: "triangle",
            pygame.K_q: "l",
            pygame.K_w: "r",
            pygame.K_RETURN: "start",
            pygame.K_SPACE: "select",
        }
        
        if event.key in key_map:
            button = key_map[event.key]
            self.emulator.input_controller.press(button)
        
        elif event.key == pygame.K_F1:
            self.show_debug = not self.show_debug
        
        elif event.key == pygame.K_ESCAPE:
            self.running = False

    def _handle_keyup(self, event: pygame.event.EventType) -> None:
        """Handle key release events."""
        key_map = {
            pygame.K_UP: "up",
            pygame.K_DOWN: "down",
            pygame.K_LEFT: "left",
            pygame.K_RIGHT: "right",
            pygame.K_z: "cross",
            pygame.K_x: "circle",
            pygame.K_c: "square",
            pygame.K_v: "triangle",
            pygame.K_q: "l",
            pygame.K_w: "r",
            pygame.K_RETURN: "start",
            pygame.K_SPACE: "select",
        }
        
        if event.key in key_map:
            button = key_map[event.key]
            self.emulator.input_controller.release(button)

    def render(self) -> None:
        """Render the emulator display and UI."""
        self.screen.fill(self.BLACK)
        
        # Draw PSP screen area
        self._draw_psp_screen()
        
        # Draw UI elements
        self._draw_ui()
        
        # Draw debug info if enabled
        if self.show_debug:
            self._draw_debug_info()
        
        pygame.display.flip()

    def _draw_psp_screen(self) -> None:
        """Draw the PSP framebuffer onto the pygame screen."""
        fb = self.emulator.gpu.framebuffer
        
        # Calculate scale based on window size
        scale_x = self.window_width / self.SCREEN_WIDTH
        scale_y = self.window_height / self.SCREEN_HEIGHT
        scale = min(scale_x, scale_y)
        
        # Draw framebuffer pixels
        for y in range(fb.height):
            for x in range(fb.width):
                color = fb.pixels[y][x]
                rect = pygame.Rect(
                    x * scale,
                    y * scale,
                    scale,
                    scale
                )
                pygame.draw.rect(self.screen, color, rect)

    def _draw_ui(self) -> None:
        """Draw UI elements like status, FPS, and instructions."""
        y_offset = 10
        
        # FPS counter
        fps_text = self.font_small.render(
            f"FPS: {self.clock.get_fps():.1f}",
            True,
            self.GREEN
        )
        self.screen.blit(fps_text, (10, y_offset))
        y_offset += 30
        
        # Frame counter
        frame_text = self.font_small.render(
            f"Frame: {self.frame_count}",
            True,
            self.GREEN
        )
        self.screen.blit(frame_text, (10, y_offset))
        y_offset += 30
        
        # Emulator status
        status_text = self.font_small.render(
            "Status: Running",
            True,
            self.GREEN
        )
        self.screen.blit(status_text, (10, y_offset))
        y_offset += 30
        
        # Controls info (bottom of screen)
        controls = [
            "Arrow Keys: Move",
            "Z: Cross  X: Circle  C: Square  V: Triangle",
            "Q: L  W: R  Enter: Start  Space: Select",
            "F1: Debug  ESC: Quit"
        ]
        
        y_pos = self.window_height - (len(controls) * 25) - 10
        for control in controls:
            control_text = self.font_small.render(control, True, self.GRAY)
            self.screen.blit(control_text, (10, y_pos))
            y_pos += 25

    def _draw_debug_info(self) -> None:
        """Draw debug information overlay."""
        debug_info = []
        
        # Emulator stats
        debug_info.append("=== DEBUG INFO ===")
        debug_info.append(f"ROM: {self.rom_path or 'None'}")
        debug_info.append(f"Resolution: {self.emulator.gpu.framebuffer.width}x{self.emulator.gpu.framebuffer.height}")
        
        # Input state
        input_state = self.emulator.input_controller.snapshot()
        pressed_buttons = [btn for btn, state in input_state.items() if state]
        debug_info.append(f"Buttons Pressed: {', '.join(pressed_buttons) if pressed_buttons else 'None'}")
        
        # GPU info
        gpu_summary = self.emulator.gpu.summary()
        debug_info.append(f"GPU Frame: {gpu_summary['frame_count']}")
        
        # Draw debug text on right side
        x_pos = self.window_width - 300
        y_pos = 20
        
        for line in debug_info:
            text_surface = self.font_small.render(line, True, self.BLUE)
            self.screen.blit(text_surface, (x_pos, y_pos))
            y_pos += 25

    def update(self) -> None:
        """Update emulator state each frame."""
        # Advance emulator one frame
        self.emulator.frame()
        self.frame_count += 1

    def run(self) -> None:
        """Main emulator loop."""
        print("PSP Emulator started!")
        print("Press F1 for debug info, ESC to quit")
        
        try:
            while self.running:
                if not self.handle_events():
                    break
                
                self.update()
                self.render()
                
                # Control FPS
                self.clock.tick(self.fps)
        
        finally:
            self.quit()

    def quit(self) -> None:
        """Clean up and exit."""
        print(f"Shutting down... Ran for {self.frame_count} frames")
        pygame.quit()
        sys.exit(0)


def main(rom_path: Optional[str] = None, scale: int = 2) -> None:
    """
    Run the PSP emulator with PyGame UI.
    
    Args:
        rom_path: Optional path to PSP ROM file
        scale: Screen scale factor
    """
    ui = PSPEmulatorUI(rom_path=rom_path, scale=scale)
    ui.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PSP Emulator with PyGame UI")
    parser.add_argument("--rom", type=str, help="Path to PSP ROM file")
    parser.add_argument("--scale", type=int, default=2, help="Screen scale factor")
    
    args = parser.parse_args()
    main(rom_path=args.rom, scale=args.scale)
