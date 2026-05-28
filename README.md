# fastproto

fastproto is an early work-in-progress compiler for generating small C++ header
files from `.fastproto` schema files. It is experimenting with a compact,
header-only serialization API for C++ projects.

The generated header includes the fastproto runtime, so consumers only need to
include the one generated file.

## Quick Start

Generate a header from a schema:

```sh
uv run fastproto -o generated.hpp example.fastproto
```

Use it from C++:

```cpp
#include "generated.hpp"

fastproto::Factory<fastproto::generated::my_namespace::SimpleMessage> factory;
factory.set_simple_int_field(10);

auto serialized = factory.serialize();

fastproto::Parser<fastproto::generated::my_namespace::SimpleMessage> parser;
parser.parse(serialized);
auto value = parser.get_simple_int_field();
```

Build the example:

```sh
c++ -std=c++23 example.cpp -o example
```

## Schema Syntax

Schemas are organized into namespaces and messages:

```fastproto
namespace my_namespace {

message SimpleMessage(1) {
    simple_int_field : int32;
}

message MessageWithArray(3) {
    my_array_field : array<SimpleMessage>;
}

}
```

Each message has a numeric magic value, which is used when validating parsed
buffers. Fields use `name : type;` syntax.

Currently supported field types include:

- Integers: `int8`, `int16`, `int32`, `int64`, `uint8`, `uint16`, `uint32`, `uint64`
- Floating point: `float32`, `float64`
- `bool`
- `string`
- `array<T>` for arrays of simple types/messages
- Other simple message types

Nested namespaces are supported with C++-style `::` syntax:

```fastproto
namespace my_namespace::my_sub_namespace {
    message Nested(2) {
        value : int32;
    }
}
```

## CLI

Install the command from PyPI:

```sh
pip install fastproto-compiler
```

Then run:

```sh
fastproto -o generated.hpp example.fastproto
```

You can also run it without installing it globally with uv:

```sh
uvx --from fastproto-compiler fastproto -o generated.hpp example.fastproto
```

Run from the repo with uv:

```sh
uv run fastproto -o generated.hpp example.fastproto
```

For local development, install the command from the checkout:

```sh
uv tool install --editable .
```

If `-o` is omitted, the generated header is written to stdout.

## Python Bindings

fastproto can also generate a small Python package containing pybind11 bindings
for a schema:

```sh
fastproto --python-out fastproto_example example.fastproto
```

This creates `./fastproto_example` with the generated C++ header, pybind11
binding source, `pyproject.toml`, `CMakeLists.txt`, and Python package glue. The
compiled extension module is named `_fastproto_example` and is installed inside
the `fastproto_example` package. In this mode, `--python-out` is the output
directory and package name, so `-o` is not used.

The generated directory looks like:

```text
fastproto_example/
  pyproject.toml
  CMakeLists.txt
  include/generated.hpp
  src/fastproto_example_bindings.cpp
  fastproto_example/__init__.py
```

Build the package with:

```sh
uv build fastproto_example
```

Or install it into the current environment:

```sh
uv pip install ./fastproto_example
```

Fastproto namespaces become Python submodules. For the top-level
`example.fastproto`, message factories and parsers are available under
`fastproto_example.my_namespace`:

```python
from fastproto_example.my_namespace import SimpleMessageFactory, SimpleMessageParser

factory = SimpleMessageFactory()
factory.simple_int_field = 10

data = factory.serialize()

parser = SimpleMessageParser(data)
print(parser.simple_int_field)
```

Nested fastproto namespaces map to nested Python modules:

```python
from fastproto_example.my_namespace.my_sub_namespace.my_next_sub_namespace import (
    MessageWithStringFactory,
    MessageWithStringParser,
)

factory = MessageWithStringFactory()
factory.my_int_field = 42
factory.my_string_field = "Hello from Python"

parser = MessageWithStringParser(factory.serialize())
print(parser.my_int_field, parser.my_string_field)
```

The Python binding generator is also early WIP. It currently emits a pybind11
package scaffold that can be built with scikit-build-core, and it embeds the
Python binding runtime into the generated binding source.

## Design Notes

fastproto is currently optimized for low-copy serialization and parsing on
common GCC/Clang targets. Generated messages use `[[gnu::packed]]` structs, and
parsers view caller-owned byte buffers directly instead of materializing decoded
objects.

That keeps the hot path small:

- Simple messages serialize as a span over the factory-owned struct.
- Strings parse as `std::string_view` into the input buffer.
- Arrays parse as spans or indexed views into the input buffer.
- Builtin scalar values are converted to/from network byte order.

The tradeoff is that this is not trying to be a maximally portable C++ wire
format runtime. It assumes GCC/Clang-style packed-struct behavior on common
architectures. The parser currently reinterprets bytes as generated structs,
which is fast, but leans on compiler and platform behavior around packed layout,
alignment, and object lifetime.

## Status

This project is still early WIP. The schema language, generated C++ API, binary
format, and runtime are all subject to change.
