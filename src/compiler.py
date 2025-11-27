import ast as AST
import runtime as rt
program = \
"""
#---42 # result: -42
#~42   # result: -42
~(-42)   # result: -41
"""

ast = AST.parse(program)
print(AST.dump(ast, indent=4))



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
            print("Compiling USub")
            asm += f"\t not rax \n"


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
