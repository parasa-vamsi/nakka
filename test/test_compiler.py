# test_calculator.py (the unit tests)
import unittest
import src.runtime as rt
from src.compiler import Compiler


class TestCalculator(unittest.TestCase):

    def setUp(self):
        self.compiler = Compiler()

    def compile_and_run(self, program):
        asm = self.compiler.compile(program)
        ans = rt.run_asm(asm)
        return ans

    def int_ans_test(self, program, expected):
        result = self.compile_and_run(program)
        self.assertEqual(int(result), expected)


    def test_number(self):
        p = "42"
        self.int_ans_test(program=p, expected=42)

    def test_unary_negate(self):
        p = "-42"
        self.int_ans_test(program=p, expected=-42)

    def test_unary_bitwise_not(self):
        p = "~42"
        self.int_ans_test(program=p, expected=-43)

    def test_unary_multiple(self):
        p = "-~-42"
        self.int_ans_test(program=p, expected=-41)

    def test_if_expr(self):
        tests = {"-10 if 5 else 20" : -10,
                 "-10 if 0 else 20" : 20,
                 "-~7 if (~-1) else -11" : -11,
                 "-~7 if (~1) else -11" : 8,
                 "(5 if 0 else 6) if (4 if 1 else -4) else (3 if 0 else -3)" : 6
                }
        for program, expected in tests.items():
            self.int_ans_test(program, expected)

if __name__ == '__main__':
    unittest.main()
