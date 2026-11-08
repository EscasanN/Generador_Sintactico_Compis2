"""Qt-free helpers shared by the CLI and the IDE for the MIPS phase (block 4).

Consumers only present and coordinate the public results of
``src.mips.pipeline``; nothing here generates or rewrites assembly.

* :func:`text_document` / :func:`write_text_safely` -- the exact text that is
  printed or exported, written UTF-8/LF through a temporary file so a failed
  write never destroys an existing file.
* :func:`default_mars_config` -- ``MARS_JAR`` or the documented local path;
  never downloads anything.
* :func:`execution_exit_code` -- the 0/1/2 contract of the architecture.
* :func:`physical_layout` -- named rows of the physical MIPS32 frames.
* :class:`CancellableMarsRun` -- re-exported from ``src.mips.simulator``: the
  MARS runner behind ``run_mars``, cancellable and tree-killing.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.mips.diagnostics import MipsDiagnostic
from src.mips.layout import (
    ACCESS_LINK_OFFSET, CONTROL_LINK_OFFSET, GLOBAL_UNIT, HEADER_SIZE, RETURN_ADDRESS_OFFSET,
    RETURN_VALUE_OFFSET, SLOT_SIZE,
)
from src.mips.models import MarsConfig, MipsExecutionResult
from src.mips.simulator import CANCELLED, CancellableMarsRun

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARS_JAR = REPOSITORY_ROOT / 'output' / 'mips' / 'tools' / 'Mars4_5.jar'

# Program errors exit with 1; tools, limits and I/O exit with 2.
PROGRAM_FAILURES = frozenset({'runtime_error', 'simulation_error'})
EXECUTION_STATUS_NAMES = {
    'success': 'terminó correctamente',
    'runtime_error': 'error del programa',
    'simulation_error': 'error de simulación en MARS',
    'assembly_error': 'MARS rechazó el ensamblador',
    'step_limit': 'límite de pasos agotado',
    'timeout': 'tiempo agotado',
    'tool_error': 'MARS o Java no disponible',
    CANCELLED: 'cancelada por el usuario',
}


# ------------------------------------------------------------------ text and files


def text_document(text: str) -> str:
    """Text as printed or exported: always ends with exactly one final newline."""
    return text if not text or text.endswith('\n') else f'{text}\n'


def write_text_safely(path: str | Path, text: str) -> Path:
    """Write UTF-8/LF atomically: on any error an existing ``path`` is untouched."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{target.name}.', suffix='.tmp',
                                             dir=target.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return target


# ------------------------------------------------------------------ MARS configuration


def default_mars_config(environ: dict[str, str] | None = None) -> MarsConfig:
    """``MARS_JAR`` when defined, else ``output/mips/tools/Mars4_5.jar`` of the checkout."""
    environ = os.environ if environ is None else environ
    configured = environ.get('MARS_JAR')
    return MarsConfig(Path(configured) if configured else DEFAULT_MARS_JAR)


def execution_exit_code(result: MipsExecutionResult) -> int:
    """0 success; 1 error of the program; 2 tool, limit, timeout or cancellation."""
    if result.accepted:
        return 0
    return 1 if result.status in PROGRAM_FAILURES else 2


def execution_summary(result: MipsExecutionResult) -> str:
    name = EXECUTION_STATUS_NAMES.get(result.status, result.status)
    code = '-' if result.returncode is None else str(result.returncode)
    return f'{result.status} — {name} (código de proceso {code})'


# ------------------------------------------------------------------ physical layout


@dataclass(frozen=True, slots=True)
class PhysicalSlot:
    """One named region of a physical MIPS32 frame or of the static area."""

    area: str
    name: str
    address: str
    size: int
    width: int
    detail: str = ''


@dataclass(frozen=True, slots=True)
class PhysicalFrameView:
    label: str
    entry: str
    size: int
    arity: int
    abstract_size: int | None
    slots: tuple[PhysicalSlot, ...]


_HEADER = (
    (RETURN_ADDRESS_OFFSET, 'ra', 'dirección de retorno ($ra)'),
    (CONTROL_LINK_OFFSET, 'fp anterior', 'enlace de control'),
    (ACCESS_LINK_OFFSET, 'enlace de acceso', 'entorno léxico (closures)'),
    (RETURN_VALUE_OFFSET, 'valor de retorno', 'respaldo del valor devuelto'),
)


def _symbol_names(compilation: object) -> dict[int, str]:
    layouts = compilation.frontend.intermediate_result.layouts
    return {id(layout.symbol): layout.symbol.name for layout in layouts.symbols}


def physical_layout(compilation: object) -> tuple[tuple[PhysicalSlot, ...],
                                                   tuple[PhysicalFrameView, ...]]:
    """Static area and every physical frame of an accepted MIPS compilation."""
    if compilation is None or not compilation.accepted:
        return (), ()
    plan = compilation.mips.layouts
    names = _symbol_names(compilation)
    abstract = compilation.frontend.intermediate_result.layouts
    statics = tuple(
        PhysicalSlot('estático', names.get(key, '?'), location.address, location.size,
                     location.width)
        for key, location in sorted(plan.statics.items(), key=lambda item: item[1].offset)
    )
    frames = []
    for label, frame in plan.frames.items():
        try:
            abstract_size = abstract.frame_by_label(label).size
        except LookupError:
            abstract_size = None
        hidden = plan.signature(label).hidden if label != GLOBAL_UNIT else ()
        slots = [PhysicalSlot('encabezado', name, f'{offset}($fp)', SLOT_SIZE, 4, detail)
                 for offset, name, detail in _HEADER]
        for key, location in sorted(frame.parameters.items(), key=lambda item: item[1].offset):
            index = (location.offset - frame.size) // SLOT_SIZE
            if index < len(hidden):
                name, detail = hidden[index], 'parámetro oculto'
            else:
                name, detail = names.get(key, '?'), f'argumento {index}'
            slots.append(PhysicalSlot('parámetro', name, location.address, location.size,
                                      location.width, f'{detail} (área entrante)'))
        for key, location in sorted(frame.locals.items(), key=lambda item: item[1].offset):
            slots.append(PhysicalSlot('local', names.get(key, '?'), location.address,
                                      location.size, location.width))
        cells: dict[int, list] = {}
        for lease, location in frame.temporaries.items():
            cells.setdefault(location.offset, []).append((lease, location))
        for offset in sorted(cells):
            leases = sorted(lease for lease, _ in cells[offset])
            location = cells[offset][0][1]
            shared = 'celda reutilizada' if len(leases) > 1 else ''
            slots.append(PhysicalSlot('temporal', ', '.join(f't{index}' for _, index in leases),
                                      f'{offset}($fp)', location.size, location.width, shared))
        for index in range(frame.staging):
            slots.append(PhysicalSlot('argumentos salientes', f'arg{index}',
                                      f'{frame.staging_offset(index)}($fp)', SLOT_SIZE, 4,
                                      'preparados antes de jal'))
        frames.append(PhysicalFrameView(label, plan.entry_labels.get(label, 'main'), frame.size,
                                        frame.arity, abstract_size, tuple(slots)))
    return statics, tuple(frames)


def describe_physical_layout(compilation: object) -> list[str]:
    """Text form used by ``--show-mips-layout``."""
    statics, frames = physical_layout(compilation)
    plan = compilation.mips.layouts
    lines = [f'Área estática ($gp): {plan.static_size} bytes']
    lines += [f'  {slot.address:<10} {slot.name} ({slot.size} bytes, ancho {slot.width})'
              for slot in statics]
    lines.append('Frames físicos MIPS32 (offsets respecto a $fp):')
    for frame in frames:
        abstract = '' if frame.abstract_size is None else (
            f'; registro abstracto TAC: {frame.abstract_size} bytes')
        lines.append(f'  {frame.label} [{frame.entry}] — {frame.size} bytes, '
                     f'{frame.arity} argumento(s){abstract}')
        for slot in frame.slots:
            detail = f' — {slot.detail}' if slot.detail else ''
            lines.append(f'    {slot.address:<10} {slot.area:<20} {slot.name} '
                         f'({slot.size} bytes, ancho {slot.width}){detail}')
    return lines


def statistics_line(statistics: object) -> str:
    return (f"Estadísticas MIPS: {statistics['instructions']} instrucciones, "
            f"{statistics['frames']} frames, {statistics['stack_bytes']} bytes de pila, "
            f"{statistics['spills']} derrames, {statistics['reloads']} recargas")


__all__ = [
    'CANCELLED', 'CancellableMarsRun', 'DEFAULT_MARS_JAR', 'EXECUTION_STATUS_NAMES',
    'PhysicalFrameView', 'PhysicalSlot', 'default_mars_config', 'describe_physical_layout',
    'execution_exit_code', 'execution_summary', 'physical_layout', 'statistics_line',
    'text_document', 'write_text_safely',
]
