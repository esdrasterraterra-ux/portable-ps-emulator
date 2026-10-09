from __future__ import annotations

from pathlib import Path


class MemoryMap:
    """Mapa simples de memória para a emulação inicial do PSP."""

    def __init__(self, size: int = 64 * 1024 * 1024):
        self.size = size
        self._data = bytearray(size)

    def _check_bounds(self, address: int) -> None:
        if not 0 <= address < self.size:
            raise IndexError(f"Endereço fora do intervalo de memória: 0x{address:x}")

    def read_u8(self, address: int) -> int:
        self._check_bounds(address)
        return self._data[address]

    def write_u8(self, address: int, value: int) -> None:
        self._check_bounds(address)
        self._data[address] = value & 0xFF

    def read_u32(self, address: int) -> int:
        value = 0
        for offset in range(4):
            value |= self.read_u8(address + offset) << (offset * 8)
        return value & 0xFFFFFFFF

    def write_u32(self, address: int, value: int) -> None:
        value &= 0xFFFFFFFF
        for offset in range(4):
            self.write_u8(address + offset, (value >> (offset * 8)) & 0xFF)

    def load_bytes(self, address: int, payload: bytes) -> None:
        for index, byte in enumerate(payload):
            self.write_u8(address + index, byte)

    def dump_range(self, start: int, length: int) -> bytes:
        return bytes(self._data[start:start + length])


class MIPS32Core:
    """Núcleo MIPS32 mínimo para a base do emulador PSP."""

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

    def read_reg(self, index: int | str) -> int:
        if isinstance(index, str):
            for reg_index, name in self.REG_NAMES.items():
                if name == index:
                    index = reg_index
                    break
            else:
                raise KeyError(f"Registrador desconhecido: {index}")
        return self.regs[index & 0x1F]

    def write_reg(self, index: int | str, value: int) -> None:
        value &= 0xFFFFFFFF
        if isinstance(index, str):
            for reg_index, name in self.REG_NAMES.items():
                if name == index:
                    index = reg_index
                    break
            else:
                raise KeyError(f"Registrador desconhecido: {index}")
        if index != 0:
            self.regs[index & 0x1F] = value

    def _sign_extend(self, value: int, bits: int) -> int:
        sign_bit = 1 << (bits - 1)
        return (value ^ sign_bit) - sign_bit

    def step(self) -> int:
        instruction = self.memory.read_u32(self.pc)
        self.execute_instruction(instruction)
        return instruction

    def execute_instruction(self, instruction: int) -> None:
        opcode = (instruction >> 26) & 0x3F
        rs = (instruction >> 21) & 0x1F
        rt = (instruction >> 16) & 0x1F
        rd = (instruction >> 11) & 0x1F
        funct = instruction & 0x3F
        imm = instruction & 0xFFFF
        simm = self._sign_extend(imm, 16)
        target = instruction & 0x03FFFFFF

        if instruction == 0:
            return

        if opcode == 0x00:
            if funct == 0x00:
                return
            if funct == 0x20:
                self.write_reg(rd, (self.read_reg(rs) + self.read_reg(rt)) & 0xFFFFFFFF)
                return
            if funct == 0x21:
                self.write_reg(rd, (self.read_reg(rs) + self.read_reg(rt)) & 0xFFFFFFFF)
                return
            if funct == 0x22:
                self.write_reg(rd, (self.read_reg(rs) - self.read_reg(rt)) & 0xFFFFFFFF)
                return
            if funct == 0x24:
                self.write_reg(rd, self.read_reg(rs) & self.read_reg(rt))
                return
            if funct == 0x25:
                self.write_reg(rd, self.read_reg(rs) | self.read_reg(rt))
                return
            if funct == 0x27:
                self.write_reg(rd, ~(self.read_reg(rs) | self.read_reg(rt)) & 0xFFFFFFFF)
                return
            if funct == 0x2A:
                self.write_reg(rd, self.read_reg(rs) < self.read_reg(rt))
                return
            if funct == 0x08:
                self.pc = self.read_reg(rs)
                return

        if opcode == 0x03:
            self.write_reg(31, self.pc + 8)
            self.pc = (self.pc & 0xF0000000) | (target << 2)
            return

        if opcode == 0x04:
            if self.read_reg(rs) == self.read_reg(rt):
                self.pc = (self.pc + 4 + (simm << 2)) & 0xFFFFFFFF
            return

        if opcode == 0x05:
            if self.read_reg(rs) != self.read_reg(rt):
                self.pc = (self.pc + 4 + (simm << 2)) & 0xFFFFFFFF
            return

        if opcode == 0x08:
            self.write_reg(rt, (self.read_reg(rs) + simm) & 0xFFFFFFFF)
            return

        if opcode == 0x09:
            self.write_reg(rt, (self.read_reg(rs) + simm) & 0xFFFFFFFF)
            return

        if opcode == 0x0D:
            self.write_reg(rt, self.read_reg(rs) | imm)
            return

        if opcode == 0x0F:
            self.write_reg(rt, (imm << 16) & 0xFFFFFFFF)
            return

        if opcode == 0x23:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            self.write_reg(rt, self.memory.read_u32(effective_address))
            return

        if opcode == 0x2B:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            self.memory.write_u32(effective_address, self.read_reg(rt))
            return

        if opcode == 0x2F:
            effective_address = (self.read_reg(rs) + simm) & 0xFFFFFFFF
            self.write_reg(rt, self.memory.read_u32(effective_address))
            return

        raise NotImplementedError(f"Instrução MIPS não implementada: opcode 0x{opcode:02x}, instr 0x{instruction:08x}")

    def load_program(self, instructions: list[int], base_address: int = 0x08800000) -> None:
        self.pc = base_address
        for index, instruction in enumerate(instructions):
            self.memory.write_u32(base_address + index * 4, instruction)

    def snapshot(self) -> dict:
        return {
            "pc": self.pc,
            "regs": {name: self.read_reg(name) for name in [
                "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
                "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
                "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
                "t8", "t9", "gp", "sp", "fp", "ra",
            ]},
            "hi": self.hi,
            "lo": self.lo,
        }
