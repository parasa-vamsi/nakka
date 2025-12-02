import ast as AST
import src.asm as x86

# Keep this formatting to avoid IndentationError
program = \
"""

# 137 >> 4
# -137 >> 4
# -456 << -3
145 << -3

"""

class Compiler:

    def __init__(self):
        self.init()

    def init(self):
        self.count = 0
        self.ast = None
        self.asm = x86.X86AsmUtils()
        self.env = {"curr_stk_idx" : 1}
        self.use_apx = False

    def gen_sym(self, name):
        self.count += 1
        return name + "_" + str(self.count)

    def compile(self, program, print_ast=True, use_apx=False):
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
                if type(v) == bool: v = int(v)
                asm.emit_instr(f"mov rax, {v}")

            #------------------- UnaryOp expression -----------------
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

            case AST.Not():
                print("Compiling logical not")
                asm.emit_instr("cmp rax, 0")
                asm.emit_instr("sete al")
                asm.emit_instr("movzx rax, al")

            #------------------- BinaryOp expression -----------------
            case AST.BinOp(opr_left, op, opr_right) \
                | AST.Compare(opr_left, [op], [opr_right]) \
                | AST.BoolOp(op, [opr_left, opr_right]) :
                print("Compiling BinOp")
                compile_ast(opr_left)
                # Store opr_left on the stack (temp var)
                stk_offset = -8 * env["curr_stk_idx"]
                env["curr_stk_idx"] += 1
                asm.emit_instr(f"mov [rsp + {stk_offset}], rax")
                compile_ast(opr_right)
                # Reuse the stack location created for the temp to store opr_left
                env["curr_stk_idx"] -= 1

                match op:
                    case AST.Add():
                        asm.emit_instr(f"add rax, [rsp + {stk_offset}]")

                    case AST.Sub():
                        if self.use_apx:
                            asm.emit_instr(f"sub rax, [rsp + {stk_offset}], rax")
                        else:
                            asm.emit_instr("neg rax")
                            asm.emit_instr(f"add rax, [rsp + {stk_offset}]")

                    case AST.Mult():
                        asm.emit_instr(f"imul rax, [rsp + {stk_offset}]")

                    case AST.Div() | AST.Mod():
                        asm.emit_instr("mov r8, rax")
                        asm.emit_instr(f"mov rax, [rsp + {stk_offset}]")
                        #asm.emit_instr("cqto    ;") --> cqto NASM issue
                        asm.emit_instr("mov rdx, rax")
                        asm.emit_instr("sar rdx, 63")
                        asm.emit_instr("idiv r8")
                        if isinstance(op, AST.Mod):
                            asm.emit_instr("mov rax, rdx")

                    case AST.Gt() | AST.GtE() | AST.Lt() | AST.LtE() | AST.Eq() | AST.NotEq():
                        asm.emit_instr(f"cmp [rsp + {stk_offset}], rax")
                        cc_map = {AST.Gt : "g", AST.GtE : "ge", AST.Lt : "l",
                                  AST.LtE : "le", AST.Eq : "e", AST.NotEq : "ne"}
                        cc = cc_map[type(op)]
                        asm.emit_instr(f"set{cc} al")
                        asm.emit_instr("movzx rax, al")

                    case AST.And() | AST.Or() | AST.BitXor() | AST.BitAnd() | AST.BitOr():
                        op_map = {AST.And : "and", AST.Or : "or", AST.BitXor : "xor",
                                  AST.BitAnd : "and", AST.BitOr : "or"}
                        operator = op_map[type(op)]
                        asm.emit_instr(f"{operator} rax, [rsp + {stk_offset}]")

                    case AST.RShift() | AST.LShift():
                        op_map = {AST.RShift : "sar", AST.LShift : "sal"}
                        operator = op_map[type(op)]
                        # TODO: raise error for negative shift count? C/Java doesn't and returns 0
                        asm.emit_instr("mov rcx, rax")
                        asm.emit_instr(f"mov rax, [rsp + {stk_offset}]")
                        asm.emit_instr(f"{operator} rax, cl")

                    case _:
                        raise NotImplementedError("Binary op not implemented")


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
                    env[id] = env["curr_stk_idx"]
                    env["curr_stk_idx"] += 1
                stk_offset = -8 * env[id]
                asm.emit_instr(f"mov [rsp + {stk_offset }], rax")

            case unknown:
                raise NotImplementedError(f"language feature not supported for {type(unknown)}")

if __name__ == "__main__":
    asm_code = Compiler().compile(program, print_ast=True)
    import runtime as rt
    rt.run_asm(asm_code, keep_asm=True)
