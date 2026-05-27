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

        if namespace:
            out += f"namespace generated::{namespace} {{\n"

        out += "struct [[gnu::packed]] " + name[-1] + " {\nstatic constexpr bool _is_simple = " + str(simple).lower() + ";\nconst fastproto::magic magic = " + str(message.magic) + ";\n"

        field_names = set()

        for field in message.fields:
            if field.name in field_names:
                raise Exception(f"Duplicate field name {field.name} in message {name}")
            if field.name == 'magic':
                raise Exception(f"Field name 'magic' is reserved in message {name}")
            field_names.add(field.name)
            if field.type[0] == 'builtin':
                out += f"private:\nfastproto::{field.type[1]} {field.name}_;\npublic:\n"
                out += f"void set_{field.name}(fastproto::{field.type[1]} value){{ {field.name}_ = to_network_order(value); }}\n"
                out += f"fastproto::{field.type[1]} get_{field.name}() const {{ return from_network_order({field.name}_); }}\n"
            elif field.type[0] == 'array':
                if field.type[1][0] == 'builtin':
                    if field.type[1][1] == 'string':
                        raise Exception(f"Cannot use string as array element type in field {field.name} in message {name}")
                    out += f"fastproto::array<fastproto::{field.type[1][1]}> {field.name};\n"
                else:
                    if not self.messages[field.type[1]]['simple']:
                        raise Exception(f"Cannot use non-simple type {field.type[1]} in array field {field.name} in message {name}")
                    out += f"fastproto::array<{"::".join(field.type[1])}> {field.name};\n"
            else:
                out += f"{'::'.join(field.type)} {field.name};\n"
        out += "};\n"

        if namespace:
            out += "}\n"

        generated_class_name = "generated::" + namespace + "::" + name[-1]

        out += f"template<>\nclass Factory<{generated_class_name}> {{\n"

        out += f"private:\n{generated_class_name} _instance;\n"

        if not simple:
            out += "std::vector<std::byte> _buffer;\n"
        for field in message.fields:
            if field.type[0] == 'builtin':
                if field.type[1] == 'string':
                    out += f"std::string _{field.name}_data;\n"
            elif field.type[0] == 'array':
                if field.type[1][0] == 'builtin':
                    out += f"std::vector<fastproto::{field.type[1][1]}> _{field.name}_data;\n"
                else:
                    out += f"std::vector<generated::{"::".join(field.type[1])}> _{field.name}_data;\n"
            else:
                out += f"Factory<generated::{"::".join(field.type)}> _{field.name}_data;\n"

        out += "public:\n"
        out += f"const {generated_class_name}& instance() {{ return _instance; }}\n"
        for field in message.fields:
            if field.type[0] == 'builtin' and field.type[1] != 'string':
                out += f"void set_{field.name}(fastproto::{field.type[1]} value){{ _instance.set_{field.name}(value); }}\n"
            elif field.type[0] == 'builtin' and field.type[1] == 'string':
                out += f"void set_{field.name}(const std::string& value){{ _{field.name}_data = value; }}\n"
            elif field.type[0] == 'array':
                if field.type[1][0] == 'builtin':
                    out += f"void add_{field.name}(const fastproto::{field.type[1][1]}& value){{ _{field.name}_data.push_back(to_network_order(value)); }}\n"
            else:
                out += f"Factory<generated::{"::".join(field.type)}>& edit_{field.name}(){{ return _{field.name}_data; }}\n"

        out += "std::span<std::byte> serialize() {\n"
        if simple:
            for field in message.fields:
                if field.type[0] != 'builtin' or field.type[0] == 'array':
                    out += "std::memcpy((std::byte*)&_instance." + field.name + ", (std::byte*)&(_" + field.name + "_data.instance()), sizeof(_instance." + field.name + "));\n"
            out += "return std::span((std::byte*)(&_instance), sizeof(_instance));\n"
        else:
            raise NotImplementedError("Serialization for non-simple messages is not implemented yet")
        out += "}\n"

        out += "\n};\n"

        out += f"template<>\nclass Parser<{generated_class_name}> {{"
        out += "\nprivate:\n"
        out += f"{generated_class_name} _instance;\n"
        out += "\npublic:\nvoid parse(std::span<const std::byte> data) {\n"

        if simple:
            out += "if (data.size() != sizeof(_instance)) { throw std::runtime_error(\"Invalid data size\"); }\n"
            out += "std::memcpy((std::byte*)&_instance, data.data(), sizeof(_instance));\n"


        out += "}};\n\n"
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
