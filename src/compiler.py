import ast as AST
import runtime as rt
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

ast = AST.parse(program)
print(AST.dump(ast, indent=4))

count = -1
def gen_sym(name):
    global count
    count += 1
    return name + "_" + str(count)



def compile(node):
    global asm
    match node:
        case AST.Module(body):
            print("Compiling module")
            for n in body:
                compile(n)

        case AST.Expr(value=v):
            print("Compiling Expr")
            compile(v)

        case AST.Constant(value=v):
            print("Compiling Value")
            asm += f"\t mov rax, {v} \n"

        case AST.UnaryOp(op=uo, operand=opr):
            print("Compiling UnaryOp")
            compile(opr)
            compile(uo)

        case AST.USub():
            print("Compiling USub")
            asm += f"\t neg rax \n"

        case AST.Invert():
            print("Compiling Invert/negate")
            asm += f"\t not rax \n"

        #------------------- if expression -----------------
        case AST.IfExp(test=if_exp, body=then_exp, orelse=else_exp):
            print("Compiling Compare")
            compile(if_exp)
            asm += f"\t cmp rax, 0 \n"
            label_else = gen_sym("ifexp_else")
            asm += f"\t je {label_else} \n"
            compile(then_exp)
            label_done = gen_sym("ifexp_done")
            asm += f"\t jmp {label_done} \n"
            asm += f"{label_else}: \n"
            compile(else_exp)
            asm += f"{label_done}: \n"


        case unknown:
            raise NotImplementedError(f"language feature not supported for {type(unknown)}")

asm = \
"""
default rel
\t section .text
\t global _entry
_entry:
"""
compile(ast)
asm += "\t ret \n \n section .note.GNU-stack noexec"
print(asm)
rt.run_asm(asm)
