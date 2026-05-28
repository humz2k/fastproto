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

Run from the repo with uv:

```sh
uv run fastproto -o generated.hpp example.fastproto
```

Or install the command locally:

```sh
uv tool install --editable .
```

Then run:

```sh
fastproto -o generated.hpp example.fastproto
```

If `-o` is omitted, the generated header is written to stdout.

Generate a Python binding package:

```sh
fastproto --python-out fastproto_example example.fastproto
```

This creates `./fastproto_example` with the generated C++ header, pybind11
binding source, `pyproject.toml`, `CMakeLists.txt`, and Python package glue. The
compiled extension module is named `_fastproto_example` and is installed inside
the `fastproto_example` package. In this mode, `--python-out` is the output
directory and package name, so `-o` is not used. Build it with:

```sh
uv build fastproto_example
```

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
