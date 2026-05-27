# fastproto compiler

`fastproto` generates C++ headers from `.fastproto` schema files.

```sh
uv run fastproto -o ../generated/generated.hpp example.fastproto
```

Generated headers always embed the runtime from `generated/fastproto/fastproto.hpp`,
so consumers only need to include the one generated header. The embedded runtime
has an include guard, so multiple generated headers can be included together.

When no output flag is provided, the generated header is written to stdout.
