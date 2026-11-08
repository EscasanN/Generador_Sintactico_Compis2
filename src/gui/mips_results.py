"""IDE views for the MIPS phase (block 4 of Proyecto 3).

Reads only public results: ``MipsCompilationResult`` / ``MipsExecutionResult``
(``src/mips/models.py``) and the Qt-free rows of ``src/mips_consumer.py``.
Nothing here generates, assembles or runs code; the window's workers do that.

* :class:`MipsView` -- assembly with search, copy and safe ``.asm`` export.
* :class:`PhysicalLayoutPanel` -- static area and physical MIPS32 frames,
  labelled apart from the abstract TAC activation records.
* :class:`ExecutionPanel` -- MARS status, program output and tool messages.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.codegen_results import STAGE_NAMES, TacView, use_code_font
from src.main import asm_document
from src.mips_consumer import (
    execution_summary,
    physical_layout,
    statistics_line,
    write_text_safely,
)

STAGE_NAMES_MIPS = {**STAGE_NAMES, "mips": "de generación MIPS"}


def mips_rejection_message(compilation: object | None) -> str:
    """Why no assembly exists for ``compilation`` (``""`` when accepted)."""
    if compilation is None:
        return "Compile un programa para ver su ensamblador MIPS."
    if compilation.accepted:
        return ""
    stage = STAGE_NAMES_MIPS.get(compilation.failed_stage, compilation.failed_stage)
    return (
        f"No se generó MIPS: la compilación se detuvo en la fase {stage}. "
        "Revise la pestaña Resumen."
    )


def mips_diagnostic_lines(compilation: object | None) -> list[str]:
    """Diagnostics of the MIPS backend, with code and location."""
    if compilation is None or compilation.mips is None:
        return []
    lines = []
    for diagnostic in compilation.mips.diagnostics:
        location = diagnostic.location
        position = f"{location.line}:{location.column}" if location is not None else "-:-"
        lines.append(f"[!] {diagnostic.code} {position} — {diagnostic.message}")
    return lines


class MipsView(TacView):
    """Read-only MIPS32 assembly: same tools as the TAC view, safe export."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._search.setPlaceholderText("Buscar en el ensamblador (Enter = siguiente)")
        self._export_btn.setText("Exportar .asm…")

    def set_compilation(self, compilation: object | None) -> None:
        if compilation is not None and compilation.accepted:
            self._text.setPlainText(asm_document(compilation.mips.assembly))
            self._status.setText(
                f"Ensamblador MIPS32 para MARS 4.5 — "
                f"{statistics_line(compilation.mips.statistics).split(': ', 1)[1]}."
            )
            self._set_actions_enabled(True)
            return
        self._text.clear()
        message = mips_rejection_message(compilation)
        details = mips_diagnostic_lines(compilation)
        self._status.setText("\n".join([message, *details]) if details else message)
        self._set_actions_enabled(False)

    def export(self, path: str | Path) -> Path:
        """Atomic UTF-8/LF write: a failure never truncates an existing file."""
        if not self.has_tac():
            raise ValueError("no hay ensamblador aceptado para exportar")
        return write_text_safely(path, self.tac_text())


# ------------------------------------------------------------------- frames


class PhysicalLayoutPanel(QWidget):
    """Static ``$gp`` area on top; one tree node per physical frame below."""

    FRAME_HEADERS = ["Frame físico / slot", "Área", "Dirección", "Tamaño", "Ancho", "Detalle"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self._statics = QTableWidget(0, 4)
        self._statics.setHorizontalHeaderLabels(["Global", "Dirección", "Tamaño", "Ancho"])
        self._statics.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._statics.verticalHeader().setVisible(False)
        self._statics.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        splitter.addWidget(self._statics)

        self._frames = QTreeWidget()
        self._frames.setColumnCount(len(self.FRAME_HEADERS))
        self._frames.setHeaderLabels(self.FRAME_HEADERS)
        header = self._frames.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        for column, width in enumerate((260, 140, 90, 70, 65)):
            self._frames.setColumnWidth(column, width)
        splitter.addWidget(self._frames)
        splitter.setSizes([150, 450])
        layout.addWidget(splitter, 1)
        self.set_compilation(None)

    @property
    def static_table(self) -> QTableWidget:
        return self._statics

    @property
    def frame_tree(self) -> QTreeWidget:
        return self._frames

    def status_text(self) -> str:
        return self._status.text()

    def show_pending(self) -> None:
        self._statics.setRowCount(0)
        self._frames.clear()
        self._status.setText("Compilando…")

    def set_compilation(self, compilation: object | None) -> None:
        self._statics.setRowCount(0)
        self._frames.clear()
        if compilation is None or not compilation.accepted:
            message = mips_rejection_message(compilation)
            self._status.setText(message.replace("MIPS", "frames físicos MIPS", 1))
            return
        statics, frames = physical_layout(compilation)
        plan = compilation.mips.layouts
        self._status.setText(
            "Frames físicos MIPS32 de MARS (offsets en bytes respecto a $fp; los "
            "argumentos entran por encima del frame). Son la ubicación real de los "
            "registros de activación abstractos del TAC (pestaña Tabla extendida). "
            f"Área estática $gp: {plan.static_size} bytes; {len(frames)} frames."
        )
        self._statics.setRowCount(len(statics))
        for row, slot in enumerate(statics):
            for column, text in enumerate(
                (slot.name, slot.address, str(slot.size), str(slot.width))
            ):
                self._statics.setItem(row, column, QTableWidgetItem(text))
        for frame in frames:
            abstract = (
                "" if frame.abstract_size is None
                else f"registro abstracto TAC: {frame.abstract_size} bytes"
            )
            item = QTreeWidgetItem(
                [f"{frame.label}  [{frame.entry}]", "frame", "", str(frame.size), "",
                 f"{frame.arity} argumento(s); {abstract}"]
            )
            for slot in frame.slots:
                item.addChild(QTreeWidgetItem(
                    [slot.name, slot.area, slot.address, str(slot.size), str(slot.width),
                     slot.detail]
                ))
            self._frames.addTopLevelItem(item)
        if self._frames.topLevelItemCount():
            self._frames.topLevelItem(0).setExpanded(True)


# ---------------------------------------------------------------- execution


class ExecutionPanel(QWidget):
    """Explicit MARS execution: buttons, status, program output and tool messages."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        bar = QHBoxLayout()
        self.run_button = QPushButton("Ejecutar en MARS")
        self.cancel_button = QPushButton("Cancelar ejecución")
        bar.addWidget(self.run_button)
        bar.addWidget(self.cancel_button)
        bar.addStretch()
        self._config = QLabel()
        bar.addWidget(self._config)
        layout.addLayout(bar)

        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("Salida estándar del programa en MARS.")
        use_code_font(self._output)
        splitter.addWidget(self._output)
        self._tool = QPlainTextEdit()
        self._tool.setReadOnly(True)
        self._tool.setPlaceholderText("Mensajes de MARS/Java y diagnósticos de ejecución.")
        use_code_font(self._tool)
        splitter.addWidget(self._tool)
        splitter.setSizes([380, 140])
        layout.addWidget(splitter, 1)
        self.reset()

    def output_text(self) -> str:
        return self._output.toPlainText()

    def tool_text(self) -> str:
        return self._tool.toPlainText()

    def status_text(self) -> str:
        return self._status.text()

    def set_jar(self, jar: object) -> None:
        # Only the file name: a long absolute path would widen the whole window.
        self._config.setText(f"MARS: {Path(str(jar)).name}")
        self._config.setToolTip(str(jar))

    def reset(self, message: str = "Compile un programa válido y presione Ejecutar en MARS.") -> None:
        self._output.clear()
        self._tool.clear()
        self._status.setText(message)

    def show_running(self) -> None:
        self._output.clear()
        self._tool.clear()
        self._status.setText("Ejecutando en MARS… (puede cancelar)")

    def set_result(self, result: object) -> None:
        self._output.setPlainText(result.stdout)
        lines = [
            f"{diagnostic.code}: {diagnostic.message.strip()}"
            for diagnostic in result.diagnostics
        ]
        if result.stderr.strip() and not any(result.stderr.strip() in line for line in lines):
            lines.append(result.stderr.strip())
        self._tool.setPlainText("\n".join(lines))
        prefix = "Ejecución correcta" if result.accepted else "Ejecución fallida"
        self._status.setText(f"{prefix}: {execution_summary(result)}")


__all__ = [
    "ExecutionPanel",
    "MipsView",
    "PhysicalLayoutPanel",
    "mips_diagnostic_lines",
    "mips_rejection_message",
]
