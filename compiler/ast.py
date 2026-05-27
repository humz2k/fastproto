from dataclasses import dataclass

class State:
    def __init__(self, symbol: dict = {}, current_namespace: tuple[str] = (), magic_numbers: set[int] = set()):
        self.symbols = symbol
        self.current_namespace = current_namespace
        self.magic_numbers = magic_numbers


class ASTNode:
    def __init__(self):
        pass

    def eval(self, state: State):
        pass


class Identifier(ASTNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def eval(self, state: State):
        if self.name in (
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
        ):
            return ("builtin", self.name)
        return state.current_namespace + (self.name,)

    def make_explicit(self, name: str):
        return ExplicitIdentifier((self.name, name))


class ExplicitIdentifier(ASTNode):
    def __init__(self, names: tuple[str]):
        super().__init__()
        self.names = names

    def eval(self, state: State):
        return self.names

    def make_explicit(self, name: str):
        return ExplicitIdentifier(self.names + (name,))


class Type(ASTNode):
    def __init__(self, name: Identifier | ExplicitIdentifier):
        super().__init__()
        self.name = name

    def eval(self, state: State):
        return self.name.eval(state)


class ArrayType(ASTNode):
    def __init__(self, inner_type: Identifier | ExplicitIdentifier):
        super().__init__()
        self.inner_type = inner_type

    def eval(self, state: State):
        return ('array', self.inner_type.eval(state))


class Field(ASTNode):
    def __init__(self, name: str, type: Type):
        super().__init__()
        self.name = name
        self.type = type

    def eval(self, state: State):
        return f"{self.name}: {self.type.eval(state)};"

@dataclass
class PrecompileField:
    name: str
    type: tuple[str]

@dataclass
class PrecompileMessage:
    name: tuple[str]
    magic: int
    fields: tuple[PrecompileField]

class Message(ASTNode):
    def __init__(self, name: str, magic: int, fields: list[Field] = []):
        super().__init__()
        self.name = name
        self.magic = magic
        self.fields = fields

    def eval(self, state: State):
        name = state.current_namespace + (self.name,)
        if name in state.symbols:
            raise Exception(f"Message conflict: {name} is already defined")
        if self.magic in state.magic_numbers:
            raise Exception(f"Magic number conflict: {self.magic} is already used")
        state.magic_numbers.add(self.magic)
        state.symbols[name] = "message"
        out = PrecompileMessage(name, self.magic, tuple([PrecompileField(field.name, field.type.eval(state)) for field in self.fields]))
        return [out]


class NamespaceNode(ASTNode):
    def __init__(self, name: tuple[str], children: list[ASTNode] = []):
        super().__init__()
        self.name = name
        self.children = children

    def eval(self, state: State):
        current_namespace = state.current_namespace + self.name
        new_state = State(state.symbols, current_namespace, state.magic_numbers)

        for i in range(len(current_namespace)):
            if current_namespace[: i + 1] in new_state.symbols:
                if new_state.symbols[current_namespace[: i + 1]] != "namespace":
                    raise Exception(
                        f"Namespace conflict: {current_namespace[:i+1]} is already defined as a non-namespace"
                    )
            new_state.symbols[current_namespace[: i + 1]] = "namespace"

        out = []
        for child in self.children:
            out += child.eval(new_state)
        return out


class Program(ASTNode):
    def __init__(self):
        super().__init__()
        self.namespaces: list[NamespaceNode] = []

    def add_namespace(self, namespace: NamespaceNode):
        self.namespaces.append(namespace)
        return self

    def eval(self, state: State) -> list[PrecompileMessage]:
        out = []
        for namespace in self.namespaces:
            out += namespace.eval(state)
        return out
