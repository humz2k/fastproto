import unittest

from fastproto_compiler.python_generator import generate_python_code
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
        self.assertIn(
            "FASTPROTO_PYTHON_FACTORY_BUILTIN_FIELD(int32_t, x)",
            output,
        )
        self.assertIn("FASTPROTO_PYTHON_FACTORY_STRING_FIELD(text)", output)
        self.assertIn(
            "FASTPROTO_PYTHON_FACTORY_MESSAGE_ARRAY_FIELD(Point, points)",
            output,
        )
        self.assertIn(
            "FASTPROTO_PYTHON_PARSER_BUILTIN_ARRAY_FIELD(int32_t, values)",
            output,
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
