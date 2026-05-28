from __future__ import annotations

import re

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


def _validate_python_package_name(name: str):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise FastprotoError(
            f"python package name must be a valid Python identifier: {name!r}"
        )


class PythonGenerator:
    def __init__(self, messages: list[PrecompileMessage]):
        self.cpp_generator = CppGenerator(messages)
        self.raw_messages = self.cpp_generator.raw_messages

    def _ordered_messages(self) -> list[PrecompileMessage]:
        return self.cpp_generator._ordered_messages()

    def _is_simple(self, message_name: tuple[str, ...]) -> bool:
        return self.cpp_generator.is_simple(message_name)

    def _namespace(self, message_name: tuple[str, ...]) -> str:
        return "::".join(message_name[:-1])

    def _class_name(self, message_name: tuple[str, ...]) -> str:
        return message_name[-1]

    def _python_class(self, message_name: tuple[str, ...], suffix: str) -> str:
        namespace = "::".join(message_name[:-1])
        prefix = "fastproto::python::generated"
        if namespace:
            prefix = f"{prefix}::{namespace}"
        return f"{prefix}::{message_name[-1]}{suffix}"

    def _module_var(self, namespace: tuple[str, ...]) -> str:
        if not namespace:
            return "m"
        return f"module_{'_'.join(namespace)}"

    def _namespace_prefixes(self) -> list[tuple[str, ...]]:
        prefixes = set()
        for message in self.raw_messages:
            namespace = message.name[:-1]
            for index in range(1, len(namespace) + 1):
                prefixes.add(namespace[:index])
        return sorted(prefixes, key=lambda value: (len(value), value))

    def _generate_namespace_modules(self) -> str:
        out = []
        for namespace in self._namespace_prefixes():
            parent = self._module_var(namespace[:-1])
            out.append(
                f'    auto {self._module_var(namespace)} = {parent}.def_submodule("{namespace[-1]}");'
            )
        return "\n".join(out)

    def generate_init(self, *, extension_module_name: str) -> str:
        _validate_cpp_identifier(extension_module_name, label="extension_module_name")
        prefixes = self._namespace_prefixes()
        package_prefixes = {
            namespace[:-1] for namespace in prefixes if len(namespace) > 1
        }
        top_level_names = sorted({namespace[0] for namespace in prefixes})

        out = [
            "import sys",
            "",
            f"from . import {extension_module_name} as _native",
            "",
            "",
            "def _register_module(name, module, *, package=False):",
            "    if package:",
            "        module.__path__ = []",
            "    sys.modules[name] = module",
            "    return module",
            "",
            "",
        ]

        for namespace in prefixes:
            module_expr = ".".join(namespace)
            source_expr = (
                f"_native.{namespace[0]}" if len(namespace) == 1 else module_expr
            )
            package_arg = (
                ",\n    package=True," if namespace in package_prefixes else ""
            )
            out.extend(
                [
                    f"{module_expr} = _register_module(",
                    f'    __name__ + ".{".".join(namespace)}",',
                    f"    {source_expr}{package_arg}",
                    ")",
                ]
            )

        out.append(f"__all__ = {top_level_names!r}")
        return "\n".join(out) + "\n"

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
                    f"FASTPROTO_PYTHON_MUTABLE_VIEW_MESSAGE_FIELD({self._python_class(field.type, 'MutableView')}, {field.name})"
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
                    f"FASTPROTO_PYTHON_VIEW_MESSAGE_FIELD({self._python_class(field.type, 'View')}, {field.name})"
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
                        f"FASTPROTO_PYTHON_FACTORY_MESSAGE_ARRAY_FIELD({self._python_class(inner_type, 'MutableView')}, {field.name})"
                    )
                continue

            out.append(
                f"FASTPROTO_PYTHON_FACTORY_MESSAGE_FIELD({self._python_class(field.type, 'MutableView')}, {field.name})"
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
                        f"FASTPROTO_PYTHON_PARSER_MESSAGE_ARRAY_FIELD({self._python_class(inner_type, 'View')}, {field.name})"
                    )
                continue

            out.append(
                f"FASTPROTO_PYTHON_PARSER_MESSAGE_FIELD({self._python_class(field.type, 'View')}, {field.name})"
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
        class_type = self._python_class(message.name, "MutableView")
        module = self._module_var(message.name[:-1])
        out = [
            f"FASTPROTO_PYTHON_BIND_MUTABLE_VIEW_BEGIN({module}, {class_type}, {class_name})"
        ]
        for field in message.fields:
            if _is_builtin(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_BIND_PROPERTY({class_type}, {field.name})"
                )
            elif not _is_array(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_BIND_METHOD({class_type}, edit_{field.name})"
                )
        out.append("FASTPROTO_PYTHON_BIND_MUTABLE_VIEW_END()")
        return out

    def _bind_view(self, message: PrecompileMessage) -> list[str]:
        class_name = self._class_name(message.name)
        class_type = self._python_class(message.name, "View")
        module = self._module_var(message.name[:-1])
        out = [
            f"FASTPROTO_PYTHON_BIND_VIEW_BEGIN({module}, {class_type}, {class_name})"
        ]
        for field in message.fields:
            if _is_builtin(field.type) or not _is_array(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_BIND_READONLY_PROPERTY({class_type}, {field.name})"
                )
        out.append("FASTPROTO_PYTHON_BIND_VIEW_END()")
        return out

    def _bind_factory(self, message: PrecompileMessage) -> list[str]:
        class_name = self._class_name(message.name)
        class_type = self._python_class(message.name, "Factory")
        module = self._module_var(message.name[:-1])
        out = [
            f"FASTPROTO_PYTHON_BIND_FACTORY_BEGIN({module}, {class_type}, {class_name})"
        ]
        for field in message.fields:
            if _is_builtin(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_BIND_PROPERTY({class_type}, {field.name})"
                )
                continue

            if _is_array(field.type):
                out.append(
                    f"FASTPROTO_PYTHON_BIND_METHOD({class_type}, add_{field.name})"
                )
                out.append(
                    f"FASTPROTO_PYTHON_BIND_METHOD({class_type}, clear_{field.name})"
                )
                if _is_builtin(field.type[1]):
                    out.append(
                        f"FASTPROTO_PYTHON_BIND_METHOD({class_type}, size_{field.name})"
                    )
                    out.append(
                        f'FASTPROTO_PYTHON_BIND_METHOD_WITH_ARG({class_type}, get_{field.name}, "index")'
                    )
                continue

            out.append(f"FASTPROTO_PYTHON_BIND_METHOD({class_type}, edit_{field.name})")

        out.append(f"FASTPROTO_PYTHON_BIND_FACTORY_END({class_type})")
        return out

    def _bind_parser(self, message: PrecompileMessage) -> list[str]:
        class_name = self._class_name(message.name)
        class_type = self._python_class(message.name, "Parser")
        module = self._module_var(message.name[:-1])
        out = [
            f"FASTPROTO_PYTHON_BIND_PARSER_BEGIN({module}, {class_type}, {class_name})"
        ]
        for field in message.fields:
            out.append(
                f"FASTPROTO_PYTHON_BIND_READONLY_PROPERTY({class_type}, {field.name})"
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
            f"{self._generate_namespace_modules()}\n\n"
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


def _generate_pyproject(package_name: str) -> str:
    return f"""[build-system]
requires = [
    "scikit-build-core>=0.10",
    "pybind11>=2.12",
]
build-backend = "scikit_build_core.build"

[project]
name = "{package_name}"
version = "0.1.0"
description = "Generated fastproto Python bindings"
requires-python = ">=3.9"

[tool.scikit-build]
wheel.packages = ["{package_name}"]
"""


def _generate_cmake(package_name: str, extension_module_name: str) -> str:
    return f"""cmake_minimum_required(VERSION 3.20)

project({package_name} LANGUAGES CXX)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(
  {extension_module_name}
  src/{package_name}_bindings.cpp
)

target_compile_features({extension_module_name} PRIVATE cxx_std_20)

target_include_directories(
  {extension_module_name}
  PRIVATE "${{CMAKE_CURRENT_SOURCE_DIR}}/include"
)

install(TARGETS {extension_module_name} LIBRARY DESTINATION {package_name})
"""


def generate_python_package_files(
    source: str,
    *,
    package_name: str,
    source_name: str | None = None,
) -> dict[str, str]:
    _validate_python_package_name(package_name)
    extension_module_name = f"_{package_name}"
    ast = parse_source(source)
    generator = PythonGenerator(ast.eval(State()))

    return {
        "pyproject.toml": _generate_pyproject(package_name),
        "CMakeLists.txt": _generate_cmake(package_name, extension_module_name),
        f"{package_name}/__init__.py": generator.generate_init(
            extension_module_name=extension_module_name
        ),
        "include/generated.hpp": generator.cpp_generator.generate(
            source_name=source_name
        ),
        f"src/{package_name}_bindings.cpp": generator.generate(
            module_name=extension_module_name,
            generated_header="generated.hpp",
            source_name=source_name,
        ),
    }
