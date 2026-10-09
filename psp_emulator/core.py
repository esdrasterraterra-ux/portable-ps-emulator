from __future__ import annotations


class MemoryMap:
    """Mapa simples de memória para aplicações de emulação."""

    def __init__(self, size: int = 64 * 1024 * 1024):
        self.size = size
        self._data = bytearray(size)

    def _check_bounds(self, address: int) -> None:
        if not 0 <= address < self.size:
            raise IndexError(f"Endereço fora do intervalo de memória: 0x{address:x}")

    def read_u8(self, address: int) -> int:
        self._check_bounds(address)
        return self._data[address]

    def read_u16(self, address: int) -> int:
        return (self.read_u8(address) | (self.read_u8(address + 1) << 8)) & 0xFFFF

    def read_u32(self, address: int) -> int:
        value = 0
        for offset in range(4):
            value |= self.read_u8(address + offset) << (offset * 8)
        return value & 0xFFFFFFFF

    def write_u8(self, address: int, value: int) -> None:
        self._check_bounds(address)
        self._data[address] = value & 0xFF

    def write_u16(self, address: int, value: int) -> None:
        value &= 0xFFFF
        self.write_u8(address, value & 0xFF)
        self.write_u8(address + 1, (value >> 8) & 0xFF)

    def write_u32(self, address: int, value: int) -> None:
        value &= 0xFFFFFFFF
        for offset in range(4):
            self.write_u8(address + offset, (value >> (offset * 8)) & 0xFF)

    def load_bytes(self, address: int, payload: bytes) -> None:
        for index, byte in enumerate(payload):
            self.write_u8(address + index, byte)

    def dump_range(self, start: int, length: int) -> bytes:
        return bytes(self._data[start:start + length])


class PSPMemoryMap(MemoryMap):
    """Mapa de memória compatível com regiões de memória do PSP."""

    def __init__(self, size: int = 64 * 1024 * 1024):
        super().__init__(size)
        self.regions = {
            "user_ram": (0x08000000, 0x08400000),
            "vram": (0x04000000, 0x04200000),
            "scratchpad": (0x00010000, 0x00014000),
            "kernel": (0x88000000, 0x8C000000),
        }

    def region_for(self, address: int) -> str | None:
        for name, (start, end) in self.regions.items():
            if start <= address < end:
                return name
        return None


class MIPS32Core:
    """Núcleo MIPS32 básico com instruções essenciais para emulação de PSP."""

    REG_NAMES = {
        0: "zero", 1: "at", 2: "v0", 3: "v1", 4: "a0", 5: "a1", 6: "a2", 7: "a3",
        8: "t0", 9: "t1", 10: "t2", 11: "t3", 12: "t4", 13: "t5", 14: "t6", 15: "t7",
        16: "s0", 17: "s1", 18: "s2", 19: "s3", 20: "s4", 21: "s5", 22: "s6", 23: "s7",
        24: "t8", 25: "t9", 26: "k0", 27: "k1", 28: "gp", 29: "sp", 30: "fp", 31: "ra",
    }

    def __init__(self, memory: MemoryMap):
        self.memory = memory
        self.reset()

    def reset(self) -> None:
        self.regs = [0] * 32
        self.hi = 0
        self.lo = 0
        self.pc = 0x08800000

    def _resolve_name(self, name: str) -> int:
        for reg_index, reg_name in self.REG_NAMES.items():
            if reg_name == name:
                return reg_index
        raise KeyError(f"Registrador desconhecido: {name}")

    def read_reg(self, index: int | str) -> int:
        if isinstance(index, str):
            index = self._resolve_name(index)
        return self.regs[index & 0x1F]

    def write_reg(self, index: int | str, value: int) -> None:
        value &= 0xFFFFFFFF
        if isinstance(index, str):
            index = self._resolve_name(index)
        if index != 0:
            self.regs[index & 0x1F] = value

    def _sign_extend(self, value: int, bits: int) -> int:
        sign_bit = 1 << (bits - 1)
        return (value ^ sign_bit) - sign_bit

    def _branch_target(self, immediate: int) -> int:
        return (self.pc + 4 + (immediate << 2)) & 0xFFFFFFFF

    def _jump_target(self, instruction: int) -> int:
        return ((self.pc + 4) & 0xF0000000) | ((instruction & 0x03FFFFFF) << 2)

    def step(self) -> int:
        instruction = self.memory.read_u32(self.pc)
        self.execute_instruction(instruction)
        return instruction

    def execute_instruction(self, instruction: int) -> None:
        opcode = (instruction >> 26) & 0x3F
        rs = (instruction >> 21) & 0x1F
        rt = (instruction >> 16) & 0x1F
        rd = (instruction >> 11) & 0x1F
        shamt = (instruction >> 6) & 0x1F
        funct = instruction & 0x3F
        imm = instruction & 0xFFFF
        simm = self._sign_extend(imm, 16)
        next_pc = (self.pc + 4) & 0xFFFFFFFF

        if instruction == 0:
            self.pc = next_pc
            return

        if opcode == 0x00:
            if funct == 0x00:
                self.pc = next_pc
                return
            if funct == 0x02:
                self.write_reg(rd, self.read_reg(rt) >> shamt)
                self.pc = next_pc
                return
            if funct == 0x03:
                value = self.read_reg(rt) >> shamt
                self.write_reg(rd, self._sign_extend(value, 32 - shamt) if shamt else value)
                self.pc = next_pc
                return
            if funct == 0x08:
                self.pc = self.read_reg(rs)
                return
            if funct == 0x09:
                self.write_reg(rd, next_pc)
                self.pc = self.read_reg(rs)
                return
            if funct == 0x20:
                self.write_reg(rd, (self.read_reg(rs) + self.read_reg(rt)) & 0xFFFFFFFF)
                self.pc = next_pc
                return
            if funct == 0x21:
                self.write_reg(rd, (self.read_reg(rs) + self.read_reg(rt)) & 0xFFFFFFFF)
                self.pc = next_pc
                return
            if funct == 0x22:
                self.write_reg(rd, (self.read_reg(rs) - self.read_reg(rt)) & 0xFFFFFFFF)
                self.pc = next_pc
                return
            if funct == 0x24:
                self.write_reg(rd, self.read_reg(rs) & self.read_reg(rt))
                self.pc = next_pc
                return
            if funct == 0x25:
                self.write_reg(rd, self.read_reg(rs) | self.read_reg(rt))
                self.pc = next_pc
                return
            if funct == 0x26:
                self.write_reg(rd, self.read_reg(rs) ^ self.read_reg(rt))
                self.pc = next_pc
                return
            if funct == 0x27:
                self.write_reg(rd, (~(self.read_reg(rs) | self.read_reg(rt))) & 0xFFFFFFFF)
                self.pc = next_pc
                return
            if funct == 0x2A:
                self.write_reg(rd, int(self.read_reg(rs) < self.read_reg(rt)))
                self.pc = next_pc
                return

        if opcode == 0x01:
            if rt == 0x00:
                self.pc = next_pc if self.read_reg(rs) >= 0 else self._branch_target(simm)
                return
            if rt == 0x01:
                self.pc = next_pc if self.read_reg(rs) < 0 else self._branch_target(simm)
                return

        if opcode == 0x02:
            self.pc = self._jump_target(instruction)
            return

        if opcode == 0x03:
            self.write_reg(31, next_pc + 4)
            self.pc = self._jump_target(instruction)
            return

        if opcode == 0x04:
            self.pc = self._branch_target(simm) if self.read_reg(rs) == self.read_reg(rt) else next_pc
            return

        if opcode == 0x05:
            self.pc = self._branch_target(simm) if self.read_reg(rs) != self.read_reg(rt) else next_pc
            return

        if opcode == 0x08:
            self.write_reg(rt, (self.read_reg(rs) + simm) & 0xFFFFFFFF)
            self.pc = next_pc
            return

        if opcode == 0x09:
            self.write_reg(rt, (self.read_reg(rs) + simm) & 0xFFFFFFFF)
            self.pc = next_pc
            return

        if opcode == 0x0C:
            self.write_reg(rt, self.read_reg(rs) & imm)
            self.pc = next_pc
            return

        if opcode == 0x0D:
            self.write_reg(rt, self.read_reg(rs) | imm)
            self.pc = next_pc
            return

        if opcode == 0x0F:
            self.write_reg(rt, (imm << 16) & 0xFFFFFFFF)
            self.pc = next_pc
            return

        if opcode == 0x20:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            value = self.memory.read_u8(effective_address)
            if value & 0x80:
                value -= 0x100
            self.write_reg(rt, value & 0xFFFFFFFF)
            self.pc = next_pc
            return

        if opcode == 0x21:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            value = self.memory.read_u16(effective_address)
            if value & 0x8000:
                value -= 0x10000
            self.write_reg(rt, value & 0xFFFFFFFF)
            self.pc = next_pc
            return

        if opcode == 0x23:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            self.write_reg(rt, self.memory.read_u32(effective_address))
            self.pc = next_pc
            return

        if opcode == 0x24:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            self.write_reg(rt, self.memory.read_u8(effective_address))
            self.pc = next_pc
            return

        if opcode == 0x25:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            self.write_reg(rt, self.memory.read_u16(effective_address))
            self.pc = next_pc
            return

        if opcode == 0x28:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            self.memory.write_u8(effective_address, self.read_reg(rt) & 0xFF)
            self.pc = next_pc
            return

        if opcode == 0x29:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            self.memory.write_u16(effective_address, self.read_reg(rt) & 0xFFFF)
            self.pc = next_pc
            return

        if opcode == 0x2B:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            self.memory.write_u32(effective_address, self.read_reg(rt))
            self.pc = next_pc
            return

        raise NotImplementedError(f"Instrução MIPS não implementada: opcode 0x{opcode:02x}, instr 0x{instruction:08x}")

    def load_program(self, instructions: list[int], base_address: int = 0x08800000) -> None:
        self.pc = base_address
        for index, instruction in enumerate(instructions):
            self.memory.write_u32(base_address + index * 4, instruction)

    def snapshot(self) -> dict:
        regs = {}
        for reg_index, reg_name in self.REG_NAMES.items():
            regs[reg_name] = self.read_reg(reg_index)
        return {"pc": self.pc, "regs": regs, "hi": self.hi, "lo": self.lo}

    def __repr__(self) -> str:
        return f"MIPS32Core(pc=0x{self.pc:08x}, t0={self.read_reg('t0')}, t1={self.read_reg('t1')})"


__all__ = ["MemoryMap", "PSPMemoryMap", "MIPS32Core"]


path":"psp_emulator/rom_loader.py","content":"from __future__ import annotations

import struct
from pathlib import Path

from .core import PSPMemoryMap


class ROMFormatError(ValueError):
    pass


class PSPRomLoader:
    """Carregador de ROMs em formatos simples do PSP."""

    def __init__(self, memory: PSPMemoryMap | None = None):
        self.memory = memory or PSPMemoryMap()

    def detect_format(self, rom_path: str | Path) -> str:
        data = Path(rom_path).read_bytes()
        if data.startswith(b"\x7fELF"):
            return "elf"
        if data[:4] in (b"PBP\x00", b"PBP\0", b"PBP ", b"PBP"):
            return "pbp"
        return "raw"

    def load(self, rom_path: str | Path, base_address: int = 0x08800000) -> dict:
        rom = Path(rom_path)
        payload = rom.read_bytes()
        fmt = self.detect_format(rom)
        if fmt == "elf":
            return self.load_elf(payload, base_address)
        if fmt == "pbp":
            return self.load_pbp(payload, base_address)
        self.memory.load_bytes(base_address, payload[: 0x100000])
        return {"format": "raw", "entry": base_address, "size": len(payload), "address": base_address}

    def load_elf(self, payload: bytes, base_address: int = 0x08800000) -> dict:
        if len(payload) < 52 or payload[:4] != b"\x7fELF":
            raise ROMFormatError("Arquivo ELF inválido")

        if payload[5] == 1:
            endian = "<"
        elif payload[5] == 2:
            endian = ">"
        else:
            raise ROMFormatError("Formato ELF de endian desconhecido")

        e_entry = struct.unpack_from(endian + "I", payload, 24)[0]
        e_phoff = struct.unpack_from(endian + "I", payload, 28)[0]
        e_phentsize = struct.unpack_from(endian + "H", payload, 42)[0]
        e_phnum = struct.unpack_from(endian + "H", payload, 44)[0]

        loaded_segments = []
        for i in range(e_phnum):
            phoff = e_phoff + (i * e_phentsize)
            if phoff + 32 > len(payload):
                continue
            p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = struct.unpack_from(
                endian + "IIIIIIII", payload, phoff
            )
            if p_type != 1:
                continue
            segment = payload[p_offset:p_offset + p_filesz]
            self.memory.load_bytes(p_vaddr, segment)
            loaded_segments.append({"vaddr": p_vaddr, "filesz": p_filesz, "memsz": p_memsz})

        return {"format": "elf", "entry": e_entry, "segments": loaded_segments, "base_address": base_address}

    def load_pbp(self, payload: bytes, base_address: int = 0x08800000) -> dict:
        if len(payload) < 0x100:
            raise ROMFormatError("Arquivo PBP inválido")
        data_region = payload[0x100:]
        self.memory.load_bytes(base_address, data_region[: 0x100000])
        return {"format": "pbp", "entry": base_address, "size": len(data_region), "address": base_address}


__all__ = ["ROMFormatError", "PSPRomLoader"]


path":"psp_emulator/__init__.py","content":"from __future__ import annotations

from .core import MIPS32Core, MemoryMap, PSPMemoryMap
from .emulator import PSPEmulator
from .gpu import Framebuffer, PSPGPU
from .input import InputController
from .rom_loader import PSPRomLoader

__all__ = [
    "PSPEmulator",
    "MIPS32Core",
    "MemoryMap",
    "PSPMemoryMap",
    "Framebuffer",
    "PSPGPU",
    "InputController",
    "PSPRomLoader",
]
__version__ = "0.5.0"


path":"psp_emulator/emulator.py","content":"from __future__ import annotations

from pathlib import Path

from .core import MIPS32Core, PSPMemoryMap
from .gpu import PSPGPU
from .input import InputController
from .rom_loader import PSPRomLoader


class BIOS:
    def __init__(self, version: str = "PSP 6.60"):
        self.version = version

    def boot(self) -> dict:
        return {"status": "ready", "bios": self.version, "message": "BIOS PSP inicializado"}


class PSPEmulator:
    def __init__(self, rom_path: str | None = None):
        self.memory = PSPMemoryMap()
        self.cpu = MIPS32Core(self.memory)
        self.gpu = PSPGPU()
        self.input = InputController()
        self.bios = BIOS()
        self.rom_path = rom_path
        self.rom_metadata = None
        self.frame = 0

        if rom_path:
            self.load_rom(rom_path)

    def load_rom(self, rom_path: str | Path) -> None:
        rom = Path(rom_path)
        loader = PSPRomLoader(self.memory)
        self.rom_metadata = loader.load(rom, base_address=0x08800000)
        self.cpu.pc = self.rom_metadata.get("entry", 0x08800000)
        self.rom_path = str(rom)

    def load_demo_program(self) -> None:
        instructions = [
            0x24090005,
            0x240A0003,
            0x012A4020,
            0x00000000,
        ]
        self.cpu.load_program(instructions, base_address=0x08800000)
        self.gpu.clear((0, 0, 0))
        self.gpu.fill_rect(10, 10, 100, 40, (255, 0, 0))

    def press(self, *buttons: str) -> None:
        self.input.press(*buttons)

    def release(self, *buttons: str) -> None:
        self.input.release(*buttons)

    def run(self, steps: int = 1) -> None:
        for _ in range(max(0, steps)):
            self.cpu.step()
            if self.cpu.pc % 16 == 0:
                self.gpu.present()

    def run_frame(self, steps: int = 8) -> dict:
        self.frame += 1
        self.run(steps)
        return {"frame": self.frame, "input": self.input.snapshot(), "gpu": self.gpu.summary()}

    def state_summary(self) -> str:
        snapshot = self.cpu.snapshot()
        return (
            f"PC=0x{snapshot['pc']:08x} | "
            f"t0={snapshot['regs'].get('t0', 0)} | "
            f"t1={snapshot['regs'].get('t1', 0)} | "
            f"t2={snapshot['regs'].get('t2', 0)} | "
            f"a0={snapshot['regs'].get('a0', 0)} | "
            f"sp={snapshot['regs'].get('sp', 0)} | "
            f"BIOS={self.bios.boot()['bios']} | "
            f"buttons={sorted(b for b, pressed in self.input.snapshot().items() if pressed)}"
        )

    def gpu_summary(self) -> dict:
        return self.gpu.summary()

    def boot(self) -> dict:
        return {"bios": self.bios.boot(), "gpu": self.gpu_summary(), "input": self.input.snapshot()}


__all__ = ["PSPEmulator", "BIOS"]


path":"psp_emulator/main.py","content":"import argparse

from .emulator import PSPEmulator


def main(argv=None):
    parser = argparse.ArgumentParser(description="PSP Emulator prototype")
    parser.add_argument("--rom", help="Caminho para uma ROM ou arquivo binário para carregar")
    parser.add_argument("--steps", type=int, default=10, help="Número de instruções a executar")
    parser.add_argument("--demo", action="store_true", help="Executa um programa de demonstração em vez de ROM")
    parser.add_argument("--gpu-demo", action="store_true", help="Executa uma demonstração da GPU do PSP")
    parser.add_argument("--press", nargs="*", default=[], help="Botões a serem pressionados durante a execução")
    args = parser.parse_args(argv)

    emulator = PSPEmulator()

    if args.gpu_demo or args.demo:
        emulator.load_demo_program()
        print("Iniciando demonstração do emulador PSP...")
    elif args.rom:
        emulator.load_rom(args.rom)
        print(f"Carregando ROM: {args.rom}")
    else:
        emulator.load_demo_program()
        print("Nenhuma ROM especificada; executando demonstração padrão.")

    if args.press:
        emulator.press(*args.press)

    emulator.run(args.steps)
    print(emulator.state_summary())
    print(emulator.gpu_summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


path":"tests/test_phase5.py","content":"import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from psp_emulator.core import MIPS32Core, MemoryMap, PSPMemoryMap
from psp_emulator.rom_loader import PSPRomLoader


def test_memory_round_trip():
    memory = MemoryMap()
    memory.write_u32(0x1000, 0x12345678)
    assert memory.read_u32(0x1000) == 0x12345678


def test_detect_file_format_elf(tmp_path):
    elf = tmp_path / "sample.elf"
    elf.write_bytes(b"\x7fELF" + b"\x00" * 100)
    loader = PSPRomLoader()
    assert loader.detect_format(elf) == "elf"


def test_detect_file_format_pbp(tmp_path):
    pbp = tmp_path / "sample.pbp"
    pbp.write_bytes(b"PBP\x00" + b"\x00" * 64)
    loader = PSPRomLoader()
    assert loader.detect_format(pbp) == "pbp"


def test_rom_loader_raw_bytes(tmp_path):
    rom = tmp_path / "raw.bin"
    rom.write_bytes(b"\x01\x02\x03\x04\x05")
    loader = PSPRomLoader()
    meta = loader.load(rom, base_address=0x1000)
    assert meta["format"] == "raw"
    assert meta["address"] == 0x1000


def test_psp_memory_regions():
    memory = PSPMemoryMap()
    assert memory.region_for(0x08000000) == "user_ram"
    assert memory.region_for(0x04000000) == "vram"
    assert memory.region_for(0x00010000) == "scratchpad"


def test_cpu_basic_add():
    memory = MemoryMap()
    cpu = MIPS32Core(memory)
    cpu.pc = 0x1000
    memory.write_u32(0x1000, 0x24090005)
    memory.write_u32(0x1004, 0x240A0003)
    memory.write_u32(0x1008, 0x012A4020)
    cpu.step(); cpu.step(); cpu.step()
    assert cpu.read_reg("a0") == 8


path":".gitignore","content":"__pycache__/
*.pyc
.pytest_cache/
.venv/
"}