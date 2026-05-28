from __future__ import annotations

import re
from collections import Counter

from .generator import Generator as CppGenerator
from .generator import _is_array, _is_builtin
from .model import FastprotoError, PrecompileMessage, State, TypeRef
from .parser import parse_source
from .python_runtime import PYTHON_RUNTIME_HEADER

PYTHON_BUILTIN_TYPES = {
    "bool": "bool",
    "int8": "int8_t",
    "int16": "int16_t",
    "int32": "int32_t",
    "int64": "int64_t",
    "uint8": "uint8_t",
    "uint16": "uint16_t",
    "uint32": "uint32_t",
    "uint64": "uint64_t",
    "float32": "float",
    "float64": "double",
}


def _validate_cpp_identifier(name: str, *, label: str):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise FastprotoError(f"{label} must be a valid C++ identifier: {name!r}")


class PythonGenerator:
    def __init__(self, messages: list[PrecompileMessage]):
        self.cpp_generator = CppGenerator(messages)
        self.raw_messages = self.cpp_generator.raw_messages
        self._validate_python_names()

    def _validate_python_names(self):
        names = Counter(message.name[-1] for message in self.raw_messages)
        conflicts = sorted(name for name, count in names.items() if count > 1)
        if conflicts:
            formatted = ", ".join(conflicts)
            raise FastprotoError(
                "Python bindings currently require globally unique message "
                f"names; conflicts: {formatted}"
            )

    def _ordered_messages(self) -> list[PrecompileMessage]:
        return self.cpp_generator._ordered_messages()

    def _is_simple(self, message_name: tuple[str, ...]) -> bool:
        return self.cpp_generator.is_simple(message_name)

    def _namespace(self, message_name: tuple[str, ...]) -> str:
        return "::".join(message_name[:-1])

    def _class_name(self, message_name: tuple[str, ...]) -> str:
        return message_name[-1]

    def _builtin_type(self, type_ref: TypeRef) -> str:
        name = type_ref[1]
        if name == "string":
            raise FastprotoError("string must be handled as a special field type")
        return PYTHON_BUILTIN_TYPES[name]

    def _generate_mutable_view(self, message: PrecompileMessage) -> str:
        out = [
            f"FASTPROTO_PYTHON_BEGIN_MUTABLE_VIEW_DEFINITION({self._namespace(message.name)}, {self._class_name(message.name)})"
        ]
        for field in message.fields:
            if _is_builtin(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_MUTABLE_VIEW_BUILTIN_FIELD({self._builtin_type(field.type)}, {field.name})"
                )
            elif not _is_array(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_MUTABLE_VIEW_MESSAGE_FIELD({self._class_name(field.type)}, {field.name})"
                )
        out.append("FASTPROTO_PYTHON_END_MUTABLE_VIEW_DEFINITION()")
        return "\n".join(out)

    def _generate_view(self, message: PrecompileMessage) -> str:
        out = [
            f"FASTPROTO_PYTHON_BEGIN_VIEW_DEFINITION({self._namespace(message.name)}, {self._class_name(message.name)})"
        ]
        for field in message.fields:
            if _is_builtin(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_VIEW_BUILTIN_FIELD({self._builtin_type(field.type)}, {field.name})"
                )
            elif not _is_array(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_VIEW_MESSAGE_FIELD({self._class_name(field.type)}, {field.name})"
                )
        out.append("FASTPROTO_PYTHON_END_VIEW_DEFINITION()")
        return "\n".join(out)

    def _generate_factory(self, message: PrecompileMessage) -> str:
        out = [
            f"FASTPROTO_PYTHON_BEGIN_FACTORY_DEFINITION({self._namespace(message.name)}, {self._class_name(message.name)})"
        ]
        for field in message.fields:
            if _is_builtin(field.type):
                if field.type[1] == "string":
                    out.append(f"FASTPROTO_PYTHON_FACTORY_STRING_FIELD({field.name})")
                else:
                    out.append(
                        f"FASTPROTO_PYTHON_FACTORY_BUILTIN_FIELD({self._builtin_type(field.type)}, {field.name})"
                    )
                continue

            if _is_array(field.type):
                inner_type = field.type[1]
                if _is_builtin(inner_type):
                    out.append(
                        f"FASTPROTO_PYTHON_FACTORY_BUILTIN_ARRAY_FIELD({self._builtin_type(inner_type)}, {field.name})"
                    )
                else:
                    out.append(
                        f"FASTPROTO_PYTHON_FACTORY_MESSAGE_ARRAY_FIELD({self._class_name(inner_type)}, {field.name})"
                    )
                continue

            out.append(
                f"FASTPROTO_PYTHON_FACTORY_MESSAGE_FIELD({self._class_name(field.type)}, {field.name})"
            )

        out.append("FASTPROTO_PYTHON_END_FACTORY_DEFINITION()")
        return "\n".join(out)

    def _generate_parser(self, message: PrecompileMessage) -> str:
        out = [
            f"FASTPROTO_PYTHON_BEGIN_PARSER_DEFINITION({self._namespace(message.name)}, {self._class_name(message.name)})"
        ]
        for field in message.fields:
            if _is_builtin(field.type):
                if field.type[1] == "string":
                    out.append(f"FASTPROTO_PYTHON_PARSER_STRING_FIELD({field.name})")
                else:
                    out.append(
                        f"FASTPROTO_PYTHON_PARSER_BUILTIN_FIELD({self._builtin_type(field.type)}, {field.name})"
                    )
                continue

            if _is_array(field.type):
                inner_type = field.type[1]
                if _is_builtin(inner_type):
                    out.append(
                        f"FASTPROTO_PYTHON_PARSER_BUILTIN_ARRAY_FIELD({self._builtin_type(inner_type)}, {field.name})"
                    )
                else:
                    out.append(
                        f"FASTPROTO_PYTHON_PARSER_MESSAGE_ARRAY_FIELD({self._class_name(inner_type)}, {field.name})"
                    )
                continue

            out.append(
                f"FASTPROTO_PYTHON_PARSER_MESSAGE_FIELD({self._class_name(field.type)}, {field.name})"
            )

        out.append("FASTPROTO_PYTHON_END_PARSER_DEFINITION()")
        return "\n".join(out)

    def _generate_definitions(self) -> str:
        out = []
        for message in self._ordered_messages():
            if self._is_simple(message.name):
                out.append(self._generate_mutable_view(message))
                out.append(self._generate_view(message))
            out.append(self._generate_factory(message))
            out.append(self._generate_parser(message))
        return "\n\n".join(out)

    def _bind_mutable_view(self, message: PrecompileMessage) -> list[str]:
        class_name = self._class_name(message.name)
        out = [f"FASTPROTO_PYTHON_BIND_MUTABLE_VIEW_BEGIN(m, {class_name})"]
        for field in message.fields:
            if _is_builtin(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_BIND_PROPERTY({class_name}MutableView, {field.name})"
                )
            elif not _is_array(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_BIND_METHOD({class_name}MutableView, edit_{field.name})"
                )
        out.append("FASTPROTO_PYTHON_BIND_MUTABLE_VIEW_END()")
        return out

    def _bind_view(self, message: PrecompileMessage) -> list[str]:
        class_name = self._class_name(message.name)
        out = [f"FASTPROTO_PYTHON_BIND_VIEW_BEGIN(m, {class_name})"]
        for field in message.fields:
            if _is_builtin(field.type) or not _is_array(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_BIND_READONLY_PROPERTY({class_name}View, {field.name})"
                )
        out.append("FASTPROTO_PYTHON_BIND_VIEW_END()")
        return out

    def _bind_factory(self, message: PrecompileMessage) -> list[str]:
        class_name = self._class_name(message.name)
        out = [f"FASTPROTO_PYTHON_BIND_FACTORY_BEGIN(m, {class_name})"]
        for field in message.fields:
            if _is_builtin(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_BIND_PROPERTY({class_name}Factory, {field.name})"
                )
                continue

            if _is_array(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_BIND_METHOD({class_name}Factory, add_{field.name})"
                )
                out.append(
                    f"FASTPROTO_PYTHON_BIND_METHOD({class_name}Factory, clear_{field.name})"
                )
                if _is_builtin(field.type[1]):
                    out.append(
                        f"FASTPROTO_PYTHON_BIND_METHOD({class_name}Factory, size_{field.name})"
                    )
                    out.append(
                        f'FASTPROTO_PYTHON_BIND_METHOD_WITH_ARG({class_name}Factory, get_{field.name}, "index")'
                    )
                continue

            out.append(
                f"FASTPROTO_PYTHON_BIND_METHOD({class_name}Factory, edit_{field.name})"
            )

        out.append(f"FASTPROTO_PYTHON_BIND_FACTORY_END({class_name})")
        return out

    def _bind_parser(self, message: PrecompileMessage) -> list[str]:
        class_name = self._class_name(message.name)
        out = [f"FASTPROTO_PYTHON_BIND_PARSER_BEGIN(m, {class_name})"]
        for field in message.fields:
            out.append(
                f"FASTPROTO_PYTHON_BIND_READONLY_PROPERTY({class_name}Parser, {field.name})"
            )
        out.append("FASTPROTO_PYTHON_BIND_PARSER_END()")
        return out

    def _generate_bindings(self) -> str:
        out = []
        for message in self._ordered_messages():
            if self._is_simple(message.name):
                out.extend(self._bind_mutable_view(message))
                out.append("")
                out.extend(self._bind_view(message))
                out.append("")
            out.extend(self._bind_factory(message))
            out.append("")
            out.extend(self._bind_parser(message))
            out.append("")
        return "\n".join(out).strip()

    def generate(
        self,
        *,
        module_name: str,
        generated_header: str = "generated.hpp",
        source_name: str | None = None,
    ) -> str:
        _validate_cpp_identifier(module_name, label="module_name")
        generated_from = f" from {source_name}" if source_name else ""
        return (
            f"// Generated by fastproto python bindings{generated_from}. Do not edit by hand.\n"
            f'#include "{generated_header}"\n'
            "\n"
            f"{PYTHON_RUNTIME_HEADER.rstrip()}\n\n"
            f"{self._generate_definitions()}\n\n"
            f"PYBIND11_MODULE({module_name}, m) {{\n"
            f'    m.doc() = "Generated fastproto bindings";\n\n'
            f"{self._generate_bindings()}\n"
            "}\n"
        )


def generate_python_code(
    source: str,
    *,
    module_name: str,
    generated_header: str = "generated.hpp",
    source_name: str | None = None,
) -> str:
    ast = parse_source(source)
    return PythonGenerator(ast.eval(State())).generate(
        module_name=module_name,
        generated_header=generated_header,
        source_name=source_name,
    )
