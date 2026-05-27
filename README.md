# fastproto

The compiler is packaged as the `fastproto` command in `compiler/`.

```sh
cd compiler
uv run fastproto -o ../generated/generated.hpp example.fastproto
```

Generated headers embed the fastproto C++ runtime by default, so downstream C++
projects can include the generated header directly.
