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

## Status

This project is still early WIP. The schema language, generated C++ API, binary
format, and runtime are all subject to change.
