"""Deterministic assembly, checked references and typed memory operations."""
import re
import struct

from src.mips.diagnostics import MipsError
from src.mips.models import MachineLocation
from src.semantic.diagnostics import SourceLocation


class MipsEmitter:
    def __init__(self) -> None:
        self.text: list[str] = []
        self.data: list[str] = []
        self.definitions: set[str] = set()
        self.references: set[str] = set()
        self.source_map: dict[int, SourceLocation] = {}
        self._serial = 0
        self._constants: dict[bytes, str] = {}

    def label(self, hint: str = 'label') -> str:
        name = f'_m{self._serial}_{hint.encode("utf-8").hex()}'
        self._serial += 1
        return name

    def define(self, label: str) -> None:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', label):
            raise MipsError('MIPS-LABEL', f'invalid label {label}')
        if label in self.definitions:
            raise MipsError('MIPS-LABEL-DUPLICATE', label)
        self.definitions.add(label)

    def mark(self, label: str) -> None:
        self.define(label)
        self.text.append(f'{label}:')

    def emit(self, mnemonic: str, *operands: str) -> None:
        self.text.append('    ' + mnemonic + (' ' + ', '.join(operands) if operands else ''))

    def branch(self, mnemonic: str, target: str, *operands: str) -> None:
        self.references.add(target)
        self.emit(mnemonic, *operands, target)
        self.emit('nop')

    def double(self, value: float) -> str:
        bits = struct.pack('<d', value)
        if bits not in self._constants:
            label = self.label('double')
            self.define(label)
            lo, hi = struct.unpack('<II', bits)
            self.data.extend(['.align 3', f'{label}: .word 0x{lo:08x}, 0x{hi:08x}'])
            self._constants[bits] = label
        return self._constants[bits]

    def ascii(self, value: str) -> str:
        label = self.label('ascii')
        self.define(label)
        self.data.append(f'{label}: .byte ' + ', '.join(str(x) for x in value.encode('ascii') + b'\0'))
        return label

    def load(self, register: str, location: MachineLocation) -> None:
        mnemonic = {1: 'lbu', 4: 'lw', 8: 'l.d'}[location.width]
        self.emit(mnemonic, register, location.address)

    def store(self, register: str, location: MachineLocation) -> None:
        mnemonic = {1: 'sb', 4: 'sw', 8: 's.d'}[location.width]
        self.emit(mnemonic, register, location.address)

    def render(self) -> str:
        missing = self.references - self.definitions
        if missing:
            raise MipsError('MIPS-LABEL-MISSING', ', '.join(sorted(missing)))
        return '\n'.join(['.data', *self.data, '.text', '.globl main', *self.text]) + '\n'
