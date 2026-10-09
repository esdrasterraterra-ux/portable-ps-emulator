from __future__ import annotations


class MemoryMap:
    """Mapeamento simples de memória para uso em emulação."""

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
    """Mapa de memória que simula as regiões principais do PSP."""

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
    """Núcleo MIPS32 básico com suporte a instruções essenciais do PSP."""

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
            index = self._resolve_name(index)
        return self.regs[index & 0x1F]

    def write_reg(self, index: int | str, value: int) -> None:
        value &= 0xFFFFFFFF
        if isinstance(index, str):
            index = self._resolve_name(index)
        if index != 0:
            self.regs[index & 0x1F] = value

    def _resolve_name(self, name: str) -> int:
        for reg_index, reg_name in self.REG_NAMES.items():
            if reg_name == name:
                return reg_index
        raise KeyError(f"Registrador desconhecido: {name}")

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
