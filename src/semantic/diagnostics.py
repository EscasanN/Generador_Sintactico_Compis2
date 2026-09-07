"""Diagnósticos semánticos y coordenadas independientes del entorno de trabajo."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum


class DiagnosticSeverity(Enum):
    """Niveles de severidad que entienden los consumidores semánticos.

    ``ERROR`` rechaza la aceptación semántica, mientras que ``WARNING`` se
    puede reportar sin rechazar el resultado.

    Argumentos:
        value: Valor serializado usado para resolver un miembro del enum.

    Retorna:
        El miembro de severidad correspondiente.

    Lanza:
        ValueError: Si ``value`` no identifica ningún miembro.
    """

    ERROR = "error"
    WARNING = "warning"


class DiagnosticCategory(Enum):
    """Categorías estables utilizadas para agrupar diagnósticos semánticos.

    El enum es independiente de analizadores y entornos de presentación.

    Argumentos:
        value: Valor serializado usado para resolver un miembro del enum.

    Retorna:
        El miembro de categoría correspondiente.

    Lanza:
        ValueError: Si ``value`` no identifica ningún miembro.
    """

    TYPE = "type"
    SCOPE = "scope"
    FUNCTION = "function"
    CONTROL_FLOW = "control_flow"
    CLASS = "class"
    ARRAY = "array"
    GENERAL = "general"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Identifica un intervalo basado en uno dentro de un archivo fuente opcional.

    Argumentos:
        line: Línea inicial basada en uno.
        column: Columna inicial basada en uno.
        end_line: Línea final opcional basada en uno.
        end_column: Columna final opcional basada en uno.
        source_path: Identidad de la fuente o ruta de archivo opcional.

    Retorna:
        Una ubicación inmutable en el código fuente.

    Lanza:
        ValueError: Si alguna coordenada proporcionada es menor que uno.
    """

    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    source_path: str | None = None

    def __post_init__(self) -> None:
        """Valida que cada coordenada pública presente esté basada en uno.

        Retorna:
            ``None``.

        Lanza:
            ValueError: Si una coordenada es menor que uno.
        """
        coordinates = (self.line, self.column, self.end_line, self.end_column)
        if any(coordinate is not None and coordinate < 1 for coordinate in coordinates):
            raise ValueError("source coordinates are based on 1")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Describe un problema semántico sin provocar efectos secundarios.

    Argumentos:
        category: Dominio semántico que detectó el problema.
        severity: Indica si el problema es un error o una advertencia.
        message: Explicación legible para una persona.
        location: Ubicación basada en uno asociada con el problema.

    Retorna:
        Un registro de diagnóstico inmutable.

    Lanza:
        TypeError: Si se intenta construir sin los argumentos obligatorios.
    """

    category: DiagnosticCategory
    severity: DiagnosticSeverity
    message: str
    location: SourceLocation


class DiagnosticBag:
    """Acumula diagnósticos sin imprimir y conserva el orden de inserción.

    Argumentos:
        Ninguno.

    Retorna:
        Un acumulador mutable cuyas vistas públicas son copias inmutables.

    Lanza:
        No lanza excepciones durante la acumulación normal.
    """

    def __init__(self) -> None:
        """Crea una colección vacía de diagnósticos.

        Retorna:
            ``None``.

        Lanza:
            No lanza excepciones.
        """
        self._items: list[Diagnostic] = []

    def add(
        self,
        category: DiagnosticCategory,
        message: str,
        location: SourceLocation,
        severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    ) -> Diagnostic:
        """Agrega un diagnóstico sin imprimirlo ni lanzarlo como excepción.

        Argumentos:
            category: Dominio semántico que detectó el problema.
            message: Explicación legible para una persona.
            location: Ubicación basada en uno para el problema.
            severity: Error por defecto; se puede indicar una advertencia.

        Retorna:
            El diagnóstico que se agregó.

        Lanza:
            No lanza excepciones durante la acumulación normal.
        """
        diagnostic = Diagnostic(category, severity, message, location)
        self._items.append(diagnostic)
        return diagnostic

    def extend(self, diagnostics: Iterable[Diagnostic]) -> None:
        """Agrega diagnósticos de un iterable respetando su orden.

        Argumentos:
            diagnostics: Registros de diagnóstico que se agregarán.

        Retorna:
            ``None``.

        Lanza:
            Cualquier excepción producida al consumir el iterable recibido.
        """
        self._items.extend(diagnostics)

    @property
    def items(self) -> tuple[Diagnostic, ...]:
        """Devuelve una copia inmutable de los diagnósticos acumulados.

        Retorna:
            Una tupla en orden de inserción.

        Lanza:
            No lanza excepciones.
        """
        return tuple(self._items)

    @property
    def has_errors(self) -> bool:
        """Indica si al menos un elemento acumulado es un error.

        Retorna:
            ``True`` si existe un error; de lo contrario, ``False``.

        Lanza:
            No lanza excepciones.
        """
        return any(item.severity is DiagnosticSeverity.ERROR for item in self._items)

    def __iter__(self) -> Iterator[Diagnostic]:
        """Itera sobre una copia estable en orden de inserción."""
        return iter(self.items)

    def __len__(self) -> int:
        """Devuelve la cantidad de diagnósticos acumulados."""
        return len(self._items)
