"""Immutable, parser-independent semantic types and compatibility rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass


class Type(ABC):
    """Base class for every semantic type.

    Args:
        None. Concrete subclasses carry all type-specific data.

    Returns:
        A comparable semantic type through a concrete subclass.

    Raises:
        TypeError: If this abstract base is instantiated directly.
    """

    @abstractmethod
    def __str__(self) -> str:
        """Return the stable source-like representation of this type."""

    def __repr__(self) -> str:
        """Return the stable diagnostic representation of this type."""
        return str(self)


@dataclass(frozen=True, slots=True, repr=False)
class PrimitiveType(Type):
    """Represent a primitive type by its canonical name.

    Args:
        name: Canonical type name.

    Returns:
        An immutable primitive type.

    Raises:
        TypeError: If the required name is omitted.
    """

    name: str

    def __str__(self) -> str:
        """Return the primitive's canonical name."""
        return self.name


@dataclass(frozen=True, slots=True, repr=False)
class ArrayType(Type):
    """Represent one array dimension around an element type.

    Args:
        element_type: Type stored in each array position.

    Returns:
        An immutable array type. Nest instances for multiple dimensions.

    Raises:
        TypeError: If the required element type is omitted.
    """

    element_type: Type

    def __str__(self) -> str:
        """Return the element representation followed by ``[]``."""
        return f"{self.element_type}[]"


@dataclass(frozen=True, slots=True, repr=False, init=False)
class FunctionType(Type):
    """Represent an immutable positional function signature.

    Args:
        parameter_types: Ordered iterable of parameter types. It is copied to
            a tuple so a caller cannot mutate the signature later.
        return_type: Declared return type.

    Returns:
        An immutable function type.

    Raises:
        TypeError: If either required argument is omitted or the parameter
            collection is not iterable.
    """

    parameter_types: tuple[Type, ...]
    return_type: Type

    def __init__(self, parameter_types: Iterable[Type], return_type: Type) -> None:
        """Copy the signature into immutable fields.

        Args:
            parameter_types: Ordered iterable of parameter types.
            return_type: Declared return type.

        Returns:
            None.

        Raises:
            TypeError: If ``parameter_types`` is not iterable.
        """
        object.__setattr__(self, "parameter_types", tuple(parameter_types))
        object.__setattr__(self, "return_type", return_type)

    def __str__(self) -> str:
        """Return a compact positional signature."""
        parameters = ", ".join(str(type_) for type_ in self.parameter_types)
        return f"({parameters}) -> {self.return_type}"


@dataclass(frozen=True, slots=True, repr=False)
class ClassType(Type):
    """Represent a named class and its optional direct superclass.

    Args:
        name: Class name as declared by the language frontend.
        superclass: Optional direct superclass.

    Returns:
        An immutable class type.

    Raises:
        TypeError: If the required name is omitted.
    """

    name: str
    superclass: ClassType | None = None

    def __str__(self) -> str:
        """Return the declared class name."""
        return self.name


@dataclass(frozen=True, slots=True, repr=False)
class ErrorType(Type):
    """Mark a type already invalidated by an earlier diagnostic.

    Args:
        None.

    Returns:
        An immutable error marker.

    Raises:
        No exceptions.
    """

    def __str__(self) -> str:
        """Return an unmistakable diagnostic marker."""
        return "<error>"


@dataclass(frozen=True, slots=True, repr=False)
class UnknownType(Type):
    """Mark a type for which the frontend has insufficient information.

    Args:
        None.

    Returns:
        An immutable unknown marker.

    Raises:
        No exceptions.
    """

    def __str__(self) -> str:
        """Return an unmistakable unknown marker."""
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
    """Resolve a primitive or declared class name and apply array dimensions.

    Unknown names deliberately produce :data:`UNKNOWN`; this function never
    guesses that an undeclared name denotes a class.

    Args:
        name: Primitive or class name. Surrounding whitespace is ignored.
        array_depth: Number of array wrappers to apply, zero by default.
        class_lookup: Optional mapping or callable that resolves class names.

    Returns:
        The resolved singleton or class type, wrapped to the requested depth.

    Raises:
        ValueError: If ``array_depth`` is negative.
        TypeError: If a provided lookup is neither mapping-like nor callable,
            or if it returns a non-class value.
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
    """Check whether a source value may be assigned to a target declaration.

    Compatibility is exact except for ``integer`` to ``float`` promotion and
    assigning a subclass to one of its ancestors. Arrays and functions are
    invariant. ``ERROR`` is accepted on either side to suppress cascaded
    diagnostics. ``UNKNOWN`` is compatible only with itself. ``null`` is
    compatible only with ``null`` until the language specification confirms a
    nullable reference rule.

    Args:
        source: Type of the produced value.
        target: Declared destination type.

    Returns:
        ``True`` when the assignment is permitted; otherwise ``False``.

    Raises:
        No exceptions for valid :class:`Type` instances.
    """
    if _contains_error(source) or _contains_error(target):
        return True
    if source == target:
        return True
    if source == UNKNOWN or target == UNKNOWN:
        return False
    if source == INTEGER and target == FLOAT:
        return True
    if isinstance(source, ClassType) and isinstance(target, ClassType):
        superclass = source.superclass
        while superclass is not None:
            if superclass == target:
                return True
            superclass = superclass.superclass
    return False


def common_type(types: Iterable[Type]) -> Type:
    """Return the least common type supported by the confirmed rules.

    Numeric types promote to ``float``. Equally deep arrays join their element
    types recursively, and classes join at their nearest shared ancestor.
    Exact function signatures join; different signatures do not. An empty
    collection produces ``UNKNOWN``. Unresolved members propagate ``UNKNOWN``
    only when all known constraints could still agree. A prior ``ERROR`` or a
    known incompatibility produces ``ERROR``.

    Args:
        types: Types whose common representation is needed.

    Returns:
        A concrete common type, :data:`UNKNOWN`, or :data:`ERROR`.

    Raises:
        Any exception raised while consuming the supplied iterable.
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
    """Report whether a type is the integer or float singleton.

    Args:
        type_: Type to inspect.

    Returns:
        ``True`` only for :data:`INTEGER` and :data:`FLOAT`.

    Raises:
        No exceptions.
    """
    return type_ == INTEGER or type_ == FLOAT


def is_boolean(type_: Type) -> bool:
    """Report whether a type is the boolean singleton.

    Args:
        type_: Type to inspect.

    Returns:
        ``True`` only for :data:`BOOLEAN`.

    Raises:
        No exceptions.
    """
    return type_ == BOOLEAN


def _contains_error(type_: Type) -> bool:
    """Return whether a composite type contains the error marker."""
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
    """Return whether a composite type contains the unknown marker."""
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
    """Return whether matching compatible shapes depends on unknown content."""
    has_unknown = _contains_unknown(source) or _contains_unknown(target)
    return has_unknown and _could_match_with_unknown(source, target)


def _could_match_with_unknown(left: Type, right: Type) -> bool:
    """Check whether replacing unknown markers could make two types equal."""
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
    """Find the nearest ancestor shared by all supplied classes."""
    candidate: ClassType | None = types[0]
    while candidate is not None:
        if all(is_assignable(type_, candidate) for type_ in types[1:]):
            return candidate
        candidate = candidate.superclass
    return ERROR
