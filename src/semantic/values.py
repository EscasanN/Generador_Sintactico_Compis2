"""Valores independientes del entorno intercambiados por acciones semánticas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.semantic.diagnostics import SourceLocation
from src.semantic.types import Type


class SymbolReference(Protocol):
    """Contrato estructural para un símbolo opcional asociado a un valor.

    Argumentos:
        Ninguno. Las capas semánticas posteriores proporcionan implementaciones.

    Retorna:
        Cualquier objeto con una propiedad ``name`` de tipo cadena satisface el
        protocolo.

    Lanza:
        Este protocolo no introduce excepciones.
    """

    @property
    def name(self) -> str:
        """Devuelve el nombre del símbolo en el código fuente.

        Retorna:
            El identificador expuesto por la implementación posterior del símbolo.

        Lanza:
            Este protocolo no introduce excepciones.
        """
        ...


@dataclass(frozen=True, slots=True)
class SemanticValue:
    """Conserva el tipo y los metadatos neutrales producidos para una expresión.

    Argumentos:
        type: Tipo semántico estático.
        constant_value: Valor literal opcional conocido en compilación. ``None``
            también representa el literal nulo del lenguaje.
        assignable: Indica si el valor representa un destino válido de asignación.
        mutable: Indica si ese destino puede cambiar después de su declaración.
        symbol: Referencia estructural opcional a un símbolo de una capa posterior.
        location: Ubicación opcional en la fuente basada en uno.

    Retorna:
        Un valor inmutable sin estado del analizador, gramática, perfil ni GUI.

    Lanza:
        TypeError: Si se omite el argumento obligatorio ``type``.
    """

    type: Type
    constant_value: object | None = None
    assignable: bool = False
    mutable: bool = False
    symbol: SymbolReference | None = None
    location: SourceLocation | None = None
