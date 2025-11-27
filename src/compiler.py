import ast as AST
import runtime as rt
import asm as x86

# Keep this formatting to avoid IndentationError
program = \
"""
#---42 # result: -42
#~42   # result: -42
#~(-42)   # result: -41
# -------------- If expressions ------------
#-10 if 5 else 20  # result: -10
#-10 if 0 else 20  # result: 20

#-~7 if (~-5) else --11  # result: 8
#-~7 if (~-1) else -11  # result: -11 (~-1 = 0)
#-~7 if (~1) else -11  # result: 8 (~-7 = 8)

#5 if (~-1) else (2 if 1 else 0) # result 2
#5 if (~-1) else (2 if 0 else -5) # result -5
(5 if 0 else 6) if (4 if 1 else -4) else (3 if 0 else -3)  # result: 6

"""

class Compiler:

    def __init__(self):
        self.init()

    def init(self):
        self.count = 0
        self.ast = None
        self.asm = x86.X86AsmUtils()

    def gen_sym(self, name):
        self.count += 1
        return name + "_" + str(self.count)

    def compile(self, program, print_ast=False):
        self.init()
        self.ast = AST.parse(program)
        if print_ast: print(AST.dump(self.ast, indent=4))
        self.asm.emit_header()
        self.compile_ast(self.ast)
        self.asm.emit_tail()
        return self.asm.code


    def compile_ast(self, node):
        compile_ast = self.compile_ast
        asm = self.asm
        gen_sym = self.gen_sym

        match node:
            case AST.Module(body):
                print("Compiling module")
                for n in body:
                    compile_ast(n)

            case AST.Expr(value=v):
                print("Compiling Expr")
                compile_ast(v)

            case AST.Constant(value=v):
                print("Compiling Value")
                asm.emit_instr(f"mov rax, {v}")

            case AST.UnaryOp(op=uop, operand=opr):
                print("Compiling UnaryOp")
                compile_ast(opr)
                compile_ast(uop)

            case AST.USub():
                print("Compiling USub")
                asm.emit_instr("neg rax")

            case AST.Invert():
                print("Compiling Invert/negate")
                asm.emit_instr("not rax")

            #------------------- if expression -----------------
            case AST.IfExp(test=if_exp, body=then_exp, orelse=else_exp):
                print("Compiling If Exp")
                compile_ast(if_exp)
                asm.emit_instr("cmp rax, 0")
                label_else = gen_sym("ifexp_else")
                asm.emit_instr(f"je {label_else}")
                compile_ast(then_exp)
                label_done = gen_sym("ifexp_done")
                asm.emit_instr(f"jmp {label_done}")
                asm.emit_label(f"{label_else}")
                compile_ast(else_exp)
                asm.emit_label(f"{label_done}")

            case unknown:
                raise NotImplementedError(f"language feature not supported for {type(unknown)}")

if __name__ == "__main__":
    asm_code = Compiler().compile(program, print_ast=True)
    rt.run_asm(asm_code, keep_asm=True)
