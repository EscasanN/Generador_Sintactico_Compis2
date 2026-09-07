"""Tipos semánticos inmutables independientes del analizador sintáctico."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass


class Type(ABC):
    """Clase base para todos los tipos semánticos.

    Argumentos:
        Ninguno. Las subclases concretas contienen los datos específicos.

    Retorna:
        Un tipo semántico comparable mediante una subclase concreta.

    Lanza:
        TypeError: Si esta clase base abstracta se instancia directamente.
    """

    @abstractmethod
    def __str__(self) -> str:
        """Devuelve la representación estable del tipo similar al código fuente."""

    def __repr__(self) -> str:
        """Devuelve la representación estable del tipo para diagnósticos."""
        return str(self)


@dataclass(frozen=True, slots=True, repr=False)
class PrimitiveType(Type):
    """Representa un tipo primitivo mediante su nombre canónico.

    Argumentos:
        name: Nombre canónico del tipo.

    Retorna:
        Un tipo primitivo inmutable.

    Lanza:
        TypeError: Si se omite el nombre obligatorio.
    """

    name: str

    def __str__(self) -> str:
        """Devuelve el nombre canónico del tipo primitivo."""
        return self.name


@dataclass(frozen=True, slots=True, repr=False)
class ArrayType(Type):
    """Representa una dimensión de arreglo alrededor de un tipo de elemento.

    Argumentos:
        element_type: Tipo almacenado en cada posición del arreglo.

    Retorna:
        Un tipo de arreglo inmutable. Se anidan instancias para varias dimensiones.

    Lanza:
        TypeError: Si se omite el tipo de elemento obligatorio.
    """

    element_type: Type

    def __str__(self) -> str:
        """Devuelve la representación del elemento seguida de ``[]``."""
        return f"{self.element_type}[]"


@dataclass(frozen=True, slots=True, repr=False, init=False)
class FunctionType(Type):
    """Representa una firma posicional e inmutable de función.

    Argumentos:
        parameter_types: Iterable ordenado de tipos de parámetros. Se copia a
            una tupla para que el llamador no pueda modificar después la firma.
        return_type: Tipo de retorno declarado.

    Retorna:
        Un tipo de función inmutable.

    Lanza:
        TypeError: Si se omite algún argumento obligatorio o la colección de
            parámetros no es iterable.
    """

    parameter_types: tuple[Type, ...]
    return_type: Type

    def __init__(self, parameter_types: Iterable[Type], return_type: Type) -> None:
        """Copia la firma en campos inmutables.

        Argumentos:
            parameter_types: Iterable ordenado de tipos de parámetros.
            return_type: Tipo de retorno declarado.

        Retorna:
            ``None``.

        Lanza:
            TypeError: Si ``parameter_types`` no es iterable.
        """
        object.__setattr__(self, "parameter_types", tuple(parameter_types))
        object.__setattr__(self, "return_type", return_type)

    def __str__(self) -> str:
        """Devuelve una firma posicional compacta."""
        parameters = ", ".join(str(type_) for type_ in self.parameter_types)
        return f"({parameters}) -> {self.return_type}"


@dataclass(frozen=True, slots=True, repr=False)
class ClassType(Type):
    """Representa una clase con nombre y su superclase directa opcional.

    Argumentos:
        name: Nombre de clase declarado por la etapa frontal del lenguaje.
        superclass: Superclase directa opcional.

    Retorna:
        Un tipo de clase inmutable.

    Lanza:
        TypeError: Si se omite el nombre obligatorio.
    """

    name: str
    superclass: ClassType | None = None

    def __str__(self) -> str:
        """Devuelve el nombre declarado de la clase."""
        return self.name


@dataclass(frozen=True, slots=True, repr=False)
class ErrorType(Type):
    """Marca un tipo invalidado previamente por otro diagnóstico.

    Argumentos:
        Ninguno.

    Retorna:
        Un marcador de error inmutable.

    Lanza:
        No lanza excepciones.
    """

    def __str__(self) -> str:
        """Devuelve un marcador inequívoco para diagnósticos."""
        return "<error>"


@dataclass(frozen=True, slots=True, repr=False)
class UnknownType(Type):
    """Marca un tipo para el cual la etapa frontal no tiene información suficiente.

    Argumentos:
        Ninguno.

    Retorna:
        Un marcador desconocido e inmutable.

    Lanza:
        No lanza excepciones.
    """

    def __str__(self) -> str:
        """Devuelve un marcador inequívoco de tipo desconocido."""
        return "<unknown>"


INTEGER = PrimitiveType("integer")
FLOAT = PrimitiveType("float")
STRING = PrimitiveType("string")
BOOLEAN = PrimitiveType("boolean")
NULL = PrimitiveType("null")
VOID = PrimitiveType("void")
ERROR = ErrorType()
UNKNOWN = UnknownType()

ClassLookup = Mapping[str, ClassType] | Callable[[str], ClassType | None]

_PRIMITIVES: dict[str, PrimitiveType] = {
    type_.name: type_
    for type_ in (INTEGER, FLOAT, STRING, BOOLEAN, NULL, VOID)
}


def type_from_name(
    name: str,
    array_depth: int = 0,
    class_lookup: ClassLookup | None = None,
) -> Type:
    """Resuelve un nombre primitivo o de clase y aplica dimensiones de arreglo.

    Los nombres desconocidos producen deliberadamente :data:`UNKNOWN`; esta
    función nunca supone que un nombre no declarado representa una clase.

    Argumentos:
        name: Nombre primitivo o de clase. Se ignoran los espacios alrededor.
        array_depth: Cantidad de niveles de arreglo; cero por defecto.
        class_lookup: Mapping o callable opcional que resuelve nombres de clases.

    Retorna:
        El singleton o tipo de clase resuelto, con la profundidad solicitada.

    Lanza:
        ValueError: Si ``array_depth`` es negativo.
        TypeError: Si el mecanismo de búsqueda no es similar a un mapping ni
            callable, o si devuelve un valor que no representa una clase.
    """
    if array_depth < 0:
        raise ValueError("array_depth cannot be negative")

    normalized_name = name.strip()
    resolved: Type | None = _PRIMITIVES.get(normalized_name)
    if resolved is None and class_lookup is not None:
        if callable(class_lookup):
            resolved = class_lookup(normalized_name)
        elif isinstance(class_lookup, Mapping):
            resolved = class_lookup.get(normalized_name)
        else:
            raise TypeError("class_lookup must be a mapping or callable")
        if resolved is not None and not isinstance(resolved, ClassType):
            raise TypeError("class_lookup must resolve to ClassType or None")
    if resolved is None:
        resolved = UNKNOWN

    for _ in range(array_depth):
        resolved = ArrayType(resolved)
    return resolved


def is_assignable(source: Type, target: Type) -> bool:
    """Comprueba si un valor fuente puede asignarse a una declaración destino.

    La compatibilidad es exacta salvo la promoción de ``integer`` a ``float`` y
    la asignación de una subclase a uno de sus ancestros. Los arreglos y las
    funciones son invariantes. ``null`` puede inicializar referencias de clase
    y arreglo. ``ERROR`` se acepta en ambos lados para evitar diagnósticos en
    cascada, mientras que ``UNKNOWN`` solo es compatible consigo mismo.

    Argumentos:
        source: Tipo del valor producido.
        target: Tipo declarado del destino.

    Retorna:
        ``True`` si la asignación está permitida; de lo contrario, ``False``.

    Lanza:
        No lanza excepciones para instancias válidas de :class:`Type`.
    """
    if _contains_error(source) or _contains_error(target):
        return True
    if source == target:
        return True
    if source == UNKNOWN or target == UNKNOWN:
        return False
    if source == INTEGER and target == FLOAT:
        return True
    if source == NULL and isinstance(target, (ArrayType, ClassType)):
        return True
    if isinstance(source, ClassType) and isinstance(target, ClassType):
        superclass = source.superclass
        while superclass is not None:
            if superclass == target:
                return True
            superclass = superclass.superclass
    return False


def common_type(types: Iterable[Type]) -> Type:
    """Devuelve el tipo común mínimo permitido por las reglas confirmadas.

    Los tipos numéricos se promueven a ``float``. Los arreglos con la misma
    profundidad combinan recursivamente sus tipos de elemento, y las clases se
    combinan en su ancestro común más cercano. Las firmas de función idénticas
    se combinan; las diferentes no. Una colección vacía produce ``UNKNOWN``.
    Los miembros no resueltos propagan ``UNKNOWN`` solo si todas las
    restricciones conocidas aún podrían coincidir. Un ``ERROR`` previo o una
    incompatibilidad conocida produce ``ERROR``.

    Argumentos:
        types: Tipos cuya representación común se necesita.

    Retorna:
        Un tipo común concreto, :data:`UNKNOWN` o :data:`ERROR`.

    Lanza:
        Cualquier excepción producida al consumir el iterable recibido.
    """
    members = tuple(types)
    if not members:
        return UNKNOWN
    if any(_contains_error(type_) for type_ in members):
        return ERROR
    if any(type_ == UNKNOWN for type_ in members):
        known_members = tuple(type_ for type_ in members if type_ != UNKNOWN)
        if not known_members:
            return UNKNOWN
        known_common = common_type(known_members)
        return ERROR if known_common == ERROR else UNKNOWN

    non_null_members = tuple(type_ for type_ in members if type_ != NULL)
    if len(non_null_members) != len(members) and non_null_members:
        reference_common = common_type(non_null_members)
        if isinstance(reference_common, (ArrayType, ClassType)):
            return reference_common
        return ERROR

    first = members[0]
    if all(type_ == first for type_ in members[1:]):
        return first
    if all(is_numeric(type_) for type_ in members):
        return FLOAT if FLOAT in members else INTEGER
    if all(isinstance(type_, ArrayType) for type_ in members):
        element_common = common_type(
            type_.element_type for type_ in members if isinstance(type_, ArrayType)
        )
        return ERROR if element_common == ERROR else ArrayType(element_common)
    if all(isinstance(type_, ClassType) for type_ in members):
        return _common_class_type(
            tuple(type_ for type_ in members if isinstance(type_, ClassType))
        )
    if any(_contains_unknown(type_) for type_ in members):
        constraints_are_compatible = all(
            _could_match_with_unknown(left, right)
            for index, left in enumerate(members)
            for right in members[index + 1 :]
        )
        return UNKNOWN if constraints_are_compatible else ERROR
    return ERROR


def is_numeric(type_: Type) -> bool:
    """Indica si un tipo es el singleton de entero o flotante.

    Argumentos:
        type_: Tipo que se inspeccionará.

    Retorna:
        ``True`` únicamente para :data:`INTEGER` y :data:`FLOAT`.

    Lanza:
        No lanza excepciones.
    """
    return type_ == INTEGER or type_ == FLOAT


def is_boolean(type_: Type) -> bool:
    """Indica si un tipo es el singleton booleano.

    Argumentos:
        type_: Tipo que se inspeccionará.

    Retorna:
        ``True`` únicamente para :data:`BOOLEAN`.

    Lanza:
        No lanza excepciones.
    """
    return type_ == BOOLEAN


def _contains_error(type_: Type) -> bool:
    """Indica si un tipo compuesto contiene el marcador de error."""
    if type_ == ERROR:
        return True
    if isinstance(type_, ArrayType):
        return _contains_error(type_.element_type)
    if isinstance(type_, FunctionType):
        return _contains_error(type_.return_type) or any(
            _contains_error(parameter) for parameter in type_.parameter_types
        )
    return False


def _contains_unknown(type_: Type) -> bool:
    """Indica si un tipo compuesto contiene el marcador desconocido."""
    if type_ == UNKNOWN:
        return True
    if isinstance(type_, ArrayType):
        return _contains_unknown(type_.element_type)
    if isinstance(type_, FunctionType):
        return _contains_unknown(type_.return_type) or any(
            _contains_unknown(parameter) for parameter in type_.parameter_types
        )
    return False


def _compatibility_is_unknown(source: Type, target: Type) -> bool:
    """Indica si comparar formas compatibles depende de contenido desconocido."""
    has_unknown = _contains_unknown(source) or _contains_unknown(target)
    return has_unknown and _could_match_with_unknown(source, target)


def _could_match_with_unknown(left: Type, right: Type) -> bool:
    """Comprueba si sustituir marcadores desconocidos igualaría dos tipos."""
    if left == UNKNOWN or right == UNKNOWN:
        return True
    if isinstance(left, ArrayType) and isinstance(right, ArrayType):
        return _could_match_with_unknown(left.element_type, right.element_type)
    if isinstance(left, FunctionType) and isinstance(right, FunctionType):
        if len(left.parameter_types) != len(right.parameter_types):
            return False
        return all(
            _could_match_with_unknown(left_parameter, right_parameter)
            for left_parameter, right_parameter in zip(
                left.parameter_types, right.parameter_types
            )
        ) and _could_match_with_unknown(left.return_type, right.return_type)
    return left == right


def _common_class_type(types: tuple[ClassType, ...]) -> Type:
    """Encuentra el ancestro más cercano compartido por todas las clases."""
    candidate: ClassType | None = types[0]
    while candidate is not None:
        if all(is_assignable(type_, candidate) for type_ in types[1:]):
            return candidate
        candidate = candidate.superclass
    return ERROR
