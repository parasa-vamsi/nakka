import ast as AST
import src.asm as x86

# Keep this formatting to avoid IndentationError
program = \
"""
y: int = 5

# x = -~5
# z = ~x if x else -4
# z

"""

class Compiler:

    def __init__(self):
        self.init()

    def init(self):
        self.count = 0
        self.ast = None
        self.asm = x86.X86AsmUtils()
        self.env = {"var_stk_idx" : 1}

    def gen_sym(self, name):
        self.count += 1
        return name + "_" + str(self.count)

    def compile(self, program, print_ast=True):
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
        env = self.env

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

            #------------------- Variable binding -----------------
            #case AST.Name(id, AST.Load()): -> also works
            case AST.Name(id):
                print(f"Compiling Name Expr: {id}")
                if id in env.keys():
                    stk_offset = -8 * env[id]
                    asm.emit_instr(f"mov rax, [rsp + {stk_offset }]")
                else:
                    raise LookupError(f"Variable {id} is not assigned")

            #case AST.Assign([AST.Name(id, AST.Store())], value): -> also works
            case AST.Assign([AST.Name(id)], value):
                print("Compiling Single Assign")
                compile_ast(value)
                if id not in env.keys():
                    env[id] = env["var_stk_idx"]
                    env["var_stk_idx"] += 1
                stk_offset = -8 * env[id]
                asm.emit_instr(f"mov [rsp + {stk_offset }], rax")

            # case AST.Expr(AST.Name(id)):
            #     print("Compiling Name Expr")
            #     stk_offset = -8 * env[id]
            #     asm.emit_instr(f"mov rax, [rsp + {stk_offset }]")


            # case AST.Name(id=id):
            #     print("Compiling Name")
            #     if id not in env.keys():
            #         env[id] = env["var_stk_idx"]
            #         env["var_stk_idx"] += 1
            #     else:
            #         stk_offset = -8 * env[id]
            #         asm.emit_instr(f"mov rax, [rsp + {stk_offset }]")
            #     print(env)
            #     return id

            # case AST.Assign(targets=tgts, value=v):
            #     print("Compiling Assign")
            #     compile_ast(v)
            #     for t in tgts:
            #         id = compile_ast(t)
            #         stk_offset = -8 * env[id]
            #         asm.emit_instr(f"mov [rsp + {stk_offset }], rax")


            case unknown:
                raise NotImplementedError(f"language feature not supported for {type(unknown)}")

if __name__ == "__main__":
    asm_code = Compiler().compile(program, print_ast=True)
    import runtime as rt
    rt.run_asm(asm_code, keep_asm=True)
