import unittest

from fastproto_compiler.python_generator import (
    generate_python_code,
    generate_python_package_files,
)
from fastproto_compiler.python_runtime import PYTHON_RUNTIME_HEADER

SCHEMA = """
namespace sample {
message Point(1) {
    x: int32;
}

message Greeting(2) {
    text: string;
}

message Batch(3) {
    points: array<Point>;
    values: array<int32>;
}
}

namespace sample::inner {
message Nested(4) {
    value: int32;
}
}
"""

DUPLICATE_LEAF_SCHEMA = """
namespace one {
message Item(1) {
    value: int32;
}
}

namespace two {
message Item(2) {
    value: int32;
}
}
"""


class PythonGeneratorTests(unittest.TestCase):
    def test_generates_pybind_runtime_macros(self):
        output = generate_python_code(
            SCHEMA,
            module_name="_sample",
            source_name="sample.fastproto",
        )

        self.assertIn('#include "generated.hpp"', output)
        self.assertIn("#ifndef FASTPROTO_PYRUNTIME_HPP_INCLUDED", output)
        self.assertNotIn('#include "pyruntime.hpp"', output)
        self.assertIn("PYBIND11_MODULE(_sample, m)", output)
        self.assertIn('auto module_sample = m.def_submodule("sample");', output)
        self.assertIn(
            'auto module_sample_inner = module_sample.def_submodule("inner");',
            output,
        )
        self.assertIn(
            "FASTPROTO_PYTHON_BIND_FACTORY_BEGIN(module_sample, fastproto::python::generated::sample::PointFactory, Point)",
            output,
        )
        self.assertIn(
            "FASTPROTO_PYTHON_FACTORY_BUILTIN_FIELD(int32_t, x)",
            output,
        )
        self.assertIn("FASTPROTO_PYTHON_FACTORY_STRING_FIELD(text)", output)
        self.assertIn(
            "FASTPROTO_PYTHON_FACTORY_MESSAGE_ARRAY_FIELD(fastproto::python::generated::sample::PointMutableView, points)",
            output,
        )
        self.assertIn(
            "FASTPROTO_PYTHON_PARSER_BUILTIN_ARRAY_FIELD(int32_t, values)",
            output,
        )

    def test_python_namespaces_allow_duplicate_leaf_message_names(self):
        output = generate_python_code(
            DUPLICATE_LEAF_SCHEMA,
            module_name="_sample",
        )

        self.assertIn('auto module_one = m.def_submodule("one");', output)
        self.assertIn('auto module_two = m.def_submodule("two");', output)
        self.assertIn(
            "FASTPROTO_PYTHON_BIND_FACTORY_BEGIN(module_one, fastproto::python::generated::one::ItemFactory, Item)",
            output,
        )
        self.assertIn(
            "FASTPROTO_PYTHON_BIND_FACTORY_BEGIN(module_two, fastproto::python::generated::two::ItemFactory, Item)",
            output,
        )

    def test_generates_python_package_files(self):
        files = generate_python_package_files(
            SCHEMA,
            package_name="fastproto_example",
            source_name="sample.fastproto",
        )

        self.assertIn("pyproject.toml", files)
        self.assertIn("CMakeLists.txt", files)
        self.assertIn("fastproto_example/__init__.py", files)
        self.assertIn("include/generated.hpp", files)
        self.assertIn("src/fastproto_example_bindings.cpp", files)
        self.assertIn(
            "PYBIND11_MODULE(_fastproto_example, m)",
            files["src/fastproto_example_bindings.cpp"],
        )
        self.assertIn(
            "from . import _fastproto_example as _native",
            files["fastproto_example/__init__.py"],
        )
        self.assertIn(
            'auto module_sample = m.def_submodule("sample");',
            files["src/fastproto_example_bindings.cpp"],
        )

    def test_python_runtime_is_embedded_as_string(self):
        self.assertIn("#ifndef FASTPROTO_PYRUNTIME_HPP_INCLUDED", PYTHON_RUNTIME_HEADER)
        self.assertIn(
            "FASTPROTO_PYTHON_BEGIN_FACTORY_DEFINITION",
            PYTHON_RUNTIME_HEADER,
        )
        self.assertNotIn("#pragma once", PYTHON_RUNTIME_HEADER)


if __name__ == "__main__":
    unittest.main()
