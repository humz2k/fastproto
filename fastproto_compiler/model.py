from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

BUILTIN_TYPES = frozenset(
    {
        "bool",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "float32",
        "float64",
        "string",
    }
)

TypeRef: TypeAlias = tuple


class FastprotoError(Exception):
    """Raised when a schema cannot be compiled."""


class State:
    def __init__(
        self,
        symbols: dict[tuple[str, ...], str] | None = None,
        current_namespace: tuple[str, ...] = (),
        magic_numbers: set[int] | None = None,
    ):
        self.symbols = symbols if symbols is not None else {}
        self.current_namespace = current_namespace
        self.magic_numbers = magic_numbers if magic_numbers is not None else set()


class ASTNode:
    def eval(self, state: State):
        raise NotImplementedError


class Identifier(ASTNode):
    def __init__(self, name: str):
        self.name = name

    def eval(self, state: State):
        if self.name in BUILTIN_TYPES:
            return ("builtin", self.name)
        return state.current_namespace + (self.name,)

    def make_explicit(self, name: str):
        return ExplicitIdentifier((self.name, name))


class ExplicitIdentifier(ASTNode):
    def __init__(self, names: tuple[str, ...]):
        self.names = names

    def eval(self, state: State):
        return self.names

    def make_explicit(self, name: str):
        return ExplicitIdentifier(self.names + (name,))


class Type(ASTNode):
    def __init__(self, name: Identifier | ExplicitIdentifier):
        self.name = name

    def eval(self, state: State):
        return self.name.eval(state)


class ArrayType(ASTNode):
    def __init__(self, inner_type: Identifier | ExplicitIdentifier):
        self.inner_type = inner_type

    def eval(self, state: State):
        return ("array", self.inner_type.eval(state))


class Field(ASTNode):
    def __init__(self, name: str, field_type: Type | ArrayType):
        self.name = name
        self.type = field_type

    def eval(self, state: State):
        return PrecompileField(self.name, self.type.eval(state))


@dataclass(frozen=True)
class PrecompileField:
    name: str
    type: TypeRef


@dataclass(frozen=True)
class PrecompileMessage:
    name: tuple[str, ...]
    magic: int
    fields: tuple[PrecompileField, ...]


class Message(ASTNode):
    def __init__(self, name: str, magic: int, fields: list[Field] | None = None):
        self.name = name
        self.magic = magic
        self.fields = fields if fields is not None else []

    def eval(self, state: State):
        name = state.current_namespace + (self.name,)
        if name in state.symbols:
            raise FastprotoError(
                f"Message conflict: {'::'.join(name)} is already defined"
            )
        if self.magic in state.magic_numbers:
            raise FastprotoError(f"Magic number conflict: {self.magic} is already used")

        state.magic_numbers.add(self.magic)
        state.symbols[name] = "message"
        fields = tuple(field.eval(state) for field in self.fields)
        return [PrecompileMessage(name, self.magic, fields)]


class NamespaceNode(ASTNode):
    def __init__(self, name: tuple[str, ...], children: list[ASTNode] | None = None):
        self.name = name
        self.children = children if children is not None else []

    def eval(self, state: State):
        current_namespace = state.current_namespace + self.name
        new_state = State(state.symbols, current_namespace, state.magic_numbers)

        for index in range(len(current_namespace)):
            namespace = current_namespace[: index + 1]
            if (
                namespace in new_state.symbols
                and new_state.symbols[namespace] != "namespace"
            ):
                raise FastprotoError(
                    f"Namespace conflict: {'::'.join(namespace)} is already defined "
                    "as a non-namespace"
                )
            new_state.symbols[namespace] = "namespace"

        messages = []
        for child in self.children:
            messages.extend(child.eval(new_state))
        return messages


class Program(ASTNode):
    def __init__(self):
        self.namespaces: list[NamespaceNode] = []

    def add_namespace(self, namespace: NamespaceNode):
        self.namespaces.append(namespace)
        return self

    def eval(self, state: State) -> list[PrecompileMessage]:
        messages = []
        for namespace in self.namespaces:
            messages.extend(namespace.eval(state))
        return messages
