# fastproto Python binding prototype

This directory is a hard-coded example of what generated Python bindings for
`example.fastproto` could look like. It binds the generated header snapshot in
`include/generated.hpp` with pybind11 and packages the extension with
scikit-build-core.

## Build

From the repository root, regenerate the C++ header first:

```sh
uv run fastproto -o generated.hpp example.fastproto
```

For this prototype, copy that header into the binding package:

```sh
cp generated.hpp python_bindings/include/generated.hpp
```

Then build or install the Python package:

```sh
uv pip install -e python_bindings
```

Run the example:

```sh
python python_bindings/examples/use_bindings.py
```

## Intended Generated Shape

A future `fastproto --python-out python_bindings ...` flow could generate:

- `pyproject.toml`
- `CMakeLists.txt`
- `include/generated.hpp`
- `src/fastproto_example_bindings.cpp`
- `fastproto_example_bindings/__init__.py`

The generated binding source embeds the Python runtime helpers from
`fastproto_compiler/python_runtime.py`, just like generated C++ headers embed the
normal fastproto runtime. The binding layer keeps parser input buffers alive on
the Python side, returns `bytes` from `serialize()`, exposes scalar fields as
Python properties, and maps array fields to Python-friendly list-style views.
