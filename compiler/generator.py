from ast import State, PrecompileMessage, PrecompileField
from parser import parse
from lex import lex

class Generator:
    def __init__(self, messages: list[PrecompileMessage]):
        self.raw_messages = messages
        self.messages = {}

    def is_simple(self, message: PrecompileMessage):
        for field in message.fields:
            if field.type[0] == 'array':
                return False
            elif field.type[0] == 'builtin':
                if field.type[1] == 'string':
                    return False
            else:
                if not self.messages[field.type]['simple']:
                    return False
        return True

    def generate_message(self, message: PrecompileMessage):
        out = ""
        name = message.name
        simple = self.is_simple(message)
        self.messages[name] = {"simple": simple}
        namespace = "::".join(name[:-1])

        out += f"FASTPROTO_BEGIN_STRUCT_DEFINITION({namespace},{name[-1]},{message.magic})\n"

        factory_fields = []
        serialize_fields = []
        parser_fields = []

        field_names = set()
        for field in message.fields:
            if field.name in field_names:
                raise Exception(f"Duplicate field name {field.name} in message {name}")
            if field.name == 'magic':
                raise Exception(f"Field name 'magic' is reserved in message {name}")
            field_names.add(field.name)
            serialize_fields.append(f"FASTPROTO_FACTORY_SERIALIZE_FIELD({field.name})\n")
            if field.type[0] == 'builtin':
                if field.type[1] != 'string':
                    out += f"FASTPROTO_BUILTIN_FIELD(fastproto::{field.type[1]}, {field.name})\n"
                    factory_fields.append(f"FASTPROTO_FACTORY_BUILTIN_FIELD(fastproto::{field.type[1]}, {field.name})\n")
                    parser_fields.append(f"FASTPROTO_PARSER_BUILTIN_FIELD(fastproto::{field.type[1]}, {field.name})\n")
                else:
                    out += f"FASTPROTO_STRING_FIELD({field.name})\n"
                    factory_fields.append(f"FASTPROTO_FACTORY_STRING_FIELD({field.name})\n")
                    parser_fields.append(f"FASTPROTO_PARSER_STRING_FIELD(std::string, {field.name})\n")
            elif field.type[0] == 'array':
                if field.type[1][0] == 'builtin':
                    if field.type[1][1] == 'string':
                        raise Exception(f"Cannot use string as array element type in field {field.name} in message {name}")
                    out += f"FASTPROTO_ARRAY_FIELD(fastproto::{field.type[1][1]}, {field.name})\n"
                    factory_fields.append(f"FASTPROTO_FACTORY_ARRAY_FIELD(fastproto::{field.type[1][1]}, {field.name})\n")
                    parser_fields.append(f"FASTPROTO_PARSER_ARRAY_FIELD(fastproto::{field.type[1][1]}, {field.name})\n")
                else:
                    if not self.messages[field.type[1]]['simple']:
                        raise Exception(f"Cannot use non-simple type {field.type[1]} in array field {field.name} in message {name}")
                    out += f"FASTPROTO_ARRAY_FIELD({'::'.join(field.type[1])}, {field.name})\n"
                    factory_fields.append(f"FASTPROTO_FACTORY_ARRAY_FIELD({'::'.join(field.type[1])}, {field.name})\n")
                    parser_fields.append(f"FASTPROTO_PARSER_ARRAY_FIELD({'::'.join(field.type[1])}, {field.name})\n")
            else:
                if not self.messages[field.type]['simple']:
                    raise Exception(f"Cannot use non-simple type {'::'.join(field.type)} in field {field.name} in message {name}")
                out += f"FASTPROTO_FIELD(generated::{'::'.join(field.type)}, {field.name})\n"
                factory_fields.append(f"FASTPROTO_FACTORY_FIELD(generated::{'::'.join(field.type)}, {field.name})\n")
                parser_fields.append(f"FASTPROTO_PARSER_FIELD(generated::{'::'.join(field.type)}, {field.name})\n")

        out += "FASTPROTO_END_STRUCT_DEFINITION()\n"

        if simple:
            out += f"\nFASTPROTO_BEGIN_SIMPLE_FACTORY_DEFINITION({namespace},{name[-1]})\n"
            for field in factory_fields:
                out += field
            out += "FASTPROTO_END_SIMPLE_FACTORY_DEFINITION()\n"
        else:
            out += f"\nFASTPROTO_BEGIN_FACTORY_DEFINITION({namespace},{name[-1]})\n"
            for field in factory_fields:
                out += field
            out += "FASTPROTO_FACTORY_BEGIN_SERIALIZE()\n"
            for field in serialize_fields:
                out += field
            out += "FASTPROTO_FACTORY_END_SERIALIZE()\n"
            out += "FASTPROTO_END_FACTORY_DEFINITION()\n"

        out += f"\nFASTPROTO_BEGIN_PARSER_DEFINITION({namespace},{name[-1]})\n"
        for field in parser_fields:
            out += field
        out += "FASTPROTO_END_PARSER_DEFINITION()\n"

        return out

    def generate(self):
        out = '#pragma once\n#include "fastproto/fastproto.hpp"\n\nnamespace fastproto {\n\n'
        for message in self.raw_messages:
            out += self.generate_message(message) + "\n"
        out += "}\n"
        return out



def generate_code(source: str):
    tokens = lex(source)
    ast = parse(tokens)
    return Generator(ast.eval(State())).generate()


if __name__ == "__main__":
    import os
    with open(
        "/Users/hqureshi/Documents/fastproto/compiler/example.fastproto", "r"
    ) as f:
        raw = f.read()
    with open("/Users/hqureshi/Documents/fastproto/generated/generated.hpp","w") as f:
        f.write(generate_code(raw))
    os.system("clang-format -i /Users/hqureshi/Documents/fastproto/generated/generated.hpp")
