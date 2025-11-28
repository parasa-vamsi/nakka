# test_calculator.py (the unit tests)
import unittest
import src.runtime as rt
from src.compiler import Compiler


class TestCompiler(unittest.TestCase):

    def setUp(self):
        self.compiler = Compiler()

    def compile_and_run(self, program):
        asm = self.compiler.compile(program)
        ans = rt.run_asm(asm)
        return ans

    def run_test(self, program, expected=None):
        result = self.compile_and_run(program)
        if expected:
            self.assertEqual(int(result), expected)


    def test_number(self):
        p = "42"
        self.run_test(program=p, expected=42)

    def test_unary_negate(self):
        p = "-42"
        self.run_test(program=p, expected=-42)

    def test_unary_bitwise_not(self):
        p = "~42"
        self.run_test(program=p, expected=-43)

    def test_unary_multiple(self):
        p = "-~-42"
        self.run_test(program=p, expected=-41)

    def test_if_expr(self):
        tests = {"-10 if 5 else 20" : -10,
                 "-10 if 0 else 20" : 20,
                 "-~7 if (~-1) else -11" : -11,
                 "-~7 if (~1) else -11" : 8,
                 "(5 if 0 else 6) if (4 if 1 else -4) else (3 if 0 else -3)" : 6
                }
        for program, expected in tests.items():
            self.run_test(program, expected)

    def test_automated(self):
        expr = "~(5 if (~-1) else (-2 if 1 else ~0))"
        expected = eval(expr, {"__builtins__": None}, {})
        self.run_test(program=expr, expected=expected)

    def test_var_binding(self):
        tests = {"x = 5; x; x = 6; x" : 6,
                 "z = 4 if (~-1) else -4" : -4,
                 "x = 0; z = 4 if x else -4" : -4,
                 "x = -~5; z = ~x if x else -4; z" : -7,
                 "x = 5; z = ~5; p = -x; p" : -5,
                 "x = 0; y = 10; z = 5; p = y if x else z" : 5,
                }
        for program, expected in tests.items():
            self.run_test(program, expected)

    def test_var_unassigned(self):
        p = "x"
        with self.assertRaises(LookupError) as context:
            self.run_test(program=p)

        self.assertEqual(str(context.exception), f"Variable {p} is not assigned")


if __name__ == '__main__':
    unittest.main()
