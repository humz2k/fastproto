from __future__ import annotations

from .model import FastprotoError, PrecompileMessage, State, TypeRef
from .parser import parse_source
from .runtime import RUNTIME_HEADER


def _is_builtin(type_ref: TypeRef) -> bool:
    return len(type_ref) == 2 and type_ref[0] == "builtin"


def _is_array(type_ref: TypeRef) -> bool:
    return len(type_ref) == 2 and type_ref[0] == "array"


class Generator:
    def __init__(self, messages: list[PrecompileMessage]):
        self.raw_messages = tuple(messages)
        self.messages_by_name = {message.name: message for message in self.raw_messages}
        self.simple_cache: dict[tuple[str, ...], bool] = {}

        if len(self.messages_by_name) != len(self.raw_messages):
            raise FastprotoError("Message names must be unique")

        self._validate_references()

    def _validate_references(self):
        for message in self.raw_messages:
            field_names = set()
            for field in message.fields:
                if field.name in field_names:
                    raise FastprotoError(
                        f"Duplicate field name {field.name!r} in message "
                        f"{'::'.join(message.name)}"
                    )
                if field.name == "magic":
                    raise FastprotoError(
                        f"Field name 'magic' is reserved in message {'::'.join(message.name)}"
                    )
                field_names.add(field.name)
                self._validate_type(field.type, message, field.name)

    def _validate_type(
        self, type_ref: TypeRef, message: PrecompileMessage, field_name: str
    ):
        if _is_builtin(type_ref):
            return

        if _is_array(type_ref):
            inner_type = type_ref[1]
            if _is_builtin(inner_type):
                if inner_type[1] == "string":
                    raise FastprotoError(
                        f"Cannot use string as array element type in field "
                        f"{field_name!r} in message {'::'.join(message.name)}"
                    )
                return
            self._require_message(inner_type, message, field_name)
            return

        self._require_message(type_ref, message, field_name)

    def _require_message(
        self, type_ref: TypeRef, message: PrecompileMessage, field_name: str
    ):
        if type_ref not in self.messages_by_name:
            raise FastprotoError(
                f"Unknown type {'::'.join(type_ref)} in field {field_name!r} "
                f"of message {'::'.join(message.name)}"
            )

    def _dependencies(self, message: PrecompileMessage) -> set[tuple[str, ...]]:
        dependencies = set()
        for field in message.fields:
            if _is_builtin(field.type):
                continue
            if _is_array(field.type):
                inner_type = field.type[1]
                if not _is_builtin(inner_type):
                    dependencies.add(inner_type)
                continue
            dependencies.add(field.type)
        return dependencies

    def _ordered_messages(self) -> list[PrecompileMessage]:
        ordered = []
        visiting: set[tuple[str, ...]] = set()
        visited: set[tuple[str, ...]] = set()

        def visit(name: tuple[str, ...]):
            if name in visited:
                return
            if name in visiting:
                raise FastprotoError(
                    f"Cyclic message reference involving {'::'.join(name)}"
                )

            visiting.add(name)
            message = self.messages_by_name[name]
            for dependency in sorted(self._dependencies(message)):
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            ordered.append(message)

        for message in self.raw_messages:
            visit(message.name)
        return ordered

    def is_simple(self, message_name: tuple[str, ...]) -> bool:
        if message_name in self.simple_cache:
            return self.simple_cache[message_name]

        message = self.messages_by_name[message_name]
        for field in message.fields:
            if _is_array(field.type):
                self.simple_cache[message_name] = False
                return False
            if _is_builtin(field.type):
                if field.type[1] == "string":
                    self.simple_cache[message_name] = False
                    return False
                continue
            if not self.is_simple(field.type):
                self.simple_cache[message_name] = False
                return False

        self.simple_cache[message_name] = True
        return True

    def _message_type(self, type_ref: TypeRef) -> str:
        return f"generated::{'::'.join(type_ref)}"

    def generate_message(self, message: PrecompileMessage):
        name = message.name
        simple = self.is_simple(name)
        namespace = "::".join(name[:-1])

        out = [
            f"FASTPROTO_BEGIN_STRUCT_DEFINITION({namespace}, {name[-1]}, {message.magic})"
        ]
        factory_fields = []
        serialize_fields = []
        parser_fields = []

        for field in message.fields:
            serialize_fields.append(f"FASTPROTO_FACTORY_SERIALIZE_FIELD({field.name})")

            if _is_builtin(field.type):
                if field.type[1] == "string":
                    out.append(f"FASTPROTO_STRING_FIELD({field.name})")
                    factory_fields.append(
                        f"FASTPROTO_FACTORY_STRING_FIELD({field.name})"
                    )
                    parser_fields.append(
                        f"FASTPROTO_PARSER_STRING_FIELD(std::string, {field.name})"
                    )
                else:
                    cpp_type = f"fastproto::{field.type[1]}"
                    out.append(f"FASTPROTO_BUILTIN_FIELD({cpp_type}, {field.name})")
                    factory_fields.append(
                        f"FASTPROTO_FACTORY_BUILTIN_FIELD({cpp_type}, {field.name})"
                    )
                    parser_fields.append(
                        f"FASTPROTO_PARSER_BUILTIN_FIELD({cpp_type}, {field.name})"
                    )
                continue

            if _is_array(field.type):
                inner_type = field.type[1]
                is_builtin = _is_builtin(inner_type)
                if is_builtin:
                    cpp_type = f"fastproto::{inner_type[1]}"
                else:
                    if not self.is_simple(inner_type):
                        raise FastprotoError(
                            f"Cannot use non-simple type {'::'.join(inner_type)} "
                            f"in array field {field.name!r} in message {'::'.join(name)}"
                        )
                    cpp_type = self._message_type(inner_type)
                out.append(f"FASTPROTO_ARRAY_FIELD({cpp_type}, {field.name})")

                if is_builtin:
                    factory_fields.append(
                        f"FASTPROTO_FACTORY_BUILTIN_ARRAY_FIELD({cpp_type}, {field.name})"
                    )
                    parser_fields.append(
                        f"FASTPROTO_PARSER_BUILTIN_ARRAY_FIELD({cpp_type}, {field.name})"
                    )
                else:
                    factory_fields.append(
                        f"FASTPROTO_FACTORY_ARRAY_FIELD({cpp_type}, {field.name})"
                    )
                    parser_fields.append(
                        f"FASTPROTO_PARSER_ARRAY_FIELD({cpp_type}, {field.name})"
                    )
                continue

            if not self.is_simple(field.type):
                raise FastprotoError(
                    f"Cannot use non-simple type {'::'.join(field.type)} in field "
                    f"{field.name!r} in message {'::'.join(name)}"
                )
            cpp_type = self._message_type(field.type)
            out.append(f"FASTPROTO_FIELD({cpp_type}, {field.name})")
            factory_fields.append(f"FASTPROTO_FACTORY_FIELD({cpp_type}, {field.name})")
            parser_fields.append(f"FASTPROTO_PARSER_FIELD({cpp_type}, {field.name})")

        out.append("FASTPROTO_END_STRUCT_DEFINITION()")
        out.append("")

        if simple:
            out.append(
                f"FASTPROTO_BEGIN_SIMPLE_FACTORY_DEFINITION({namespace}, {name[-1]})"
            )
            out.extend(factory_fields)
            out.append("FASTPROTO_END_SIMPLE_FACTORY_DEFINITION()")
        else:
            out.append(f"FASTPROTO_BEGIN_FACTORY_DEFINITION({namespace}, {name[-1]})")
            out.extend(factory_fields)
            out.append("FASTPROTO_FACTORY_BEGIN_SERIALIZE()")
            out.extend(serialize_fields)
            out.append("FASTPROTO_FACTORY_END_SERIALIZE()")
            out.append("FASTPROTO_END_FACTORY_DEFINITION()")

        out.append("")
        out.append(f"FASTPROTO_BEGIN_PARSER_DEFINITION({namespace}, {name[-1]})")
        out.extend(parser_fields)
        out.append("FASTPROTO_END_PARSER_DEFINITION()")

        return "\n".join(out)

    def generate_schema_header(self):
        messages = [
            self.generate_message(message) for message in self._ordered_messages()
        ]
        return "\n\n".join(messages)

    def generate(self, *, source_name: str | None = None):
        generated_from = f" from {source_name}" if source_name else ""
        schema_header = self.generate_schema_header()
        generated_banner = (
            f"// Generated by fastproto{generated_from}. Do not edit by hand."
        )

        return (
            f"{generated_banner}\n"
            "#pragma once\n\n"
            f"{RUNTIME_HEADER.rstrip()}\n\n"
            "namespace fastproto {\n\n"
            f"{schema_header}\n\n"
            "} // namespace fastproto\n"
        )


def generate_code(source: str, *, source_name: str | None = None):
    ast = parse_source(source)
    return Generator(ast.eval(State())).generate(source_name=source_name)
