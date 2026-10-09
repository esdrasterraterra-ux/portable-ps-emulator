from __future__ import annotations

from pathlib import Path

from .core import MIPS32Core, PSPMemoryMap


class BIOS:
    def __init__(self, version: str = "PSP 6.60"):
        self.version = version

    def boot(self) -> dict:
        return {"status": "ready", "bios": self.version, "message": "BIOS PSP inicializado"}


class PSPEmulator:
    def __init__(self, rom_path: str | None = None):
        self.memory = PSPMemoryMap()
        self.cpu = MIPS32Core(self.memory)
        self.bios = BIOS()
        self.rom_path = rom_path

        if rom_path:
            self.load_rom(rom_path)

    def load_rom(self, rom_path: str | Path) -> None:
        rom = Path(rom_path)
        payload = rom.read_bytes()
        self.memory.load_bytes(0x08800000, payload[: 0x100000])
        self.cpu.pc = 0x08800000
        self.rom_path = str(rom)

    def load_demo_program(self) -> None:
        instructions = [
            0x24090005,
            0x240A0003,
            0x012A4020,
            0x05000002,
            0x00000000,
            0x00000000,
        ]
        self.cpu.load_program(instructions, base_address=0x08800000)

    def run(self, steps: int = 1) -> None:
        for _ in range(max(0, steps)):
            self.cpu.step()

    def state_summary(self) -> str:
        snapshot = self.cpu.snapshot()
        return (
            f"PC=0x{snapshot['pc']:08x} | "
            f"t0={snapshot['regs'].get('t0', 0)} | "
            f"t1={snapshot['regs'].get('t1', 0)} | "
            f"t2={snapshot['regs'].get('t2', 0)} | "
            f"a0={snapshot['regs'].get('a0', 0)} | "
            f"sp={snapshot['regs'].get('sp', 0)} | "
            f"BIOS={self.bios.boot()['bios']}"
        )

    def boot(self) -> dict:
        return self.bios.boot()
