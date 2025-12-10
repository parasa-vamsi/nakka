import ast as AST
import src.asm as x86

# Keep this formatting to avoid IndentationError
program = \
"""

# 137 >> 4
# -137 >> 4
# -456 << -3
# 145 << -3

def f1():
    x = 9; y = 7
    return (y - x) * 2

def f2():
    # x = 81; y = 9
    # return (x / y) * 2
    return -3

# x = 0
# y = 0
x = f1() - f2()
x

"""

class Environment:

    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.local_var_homes = dict()
        self.next_avialable_stk_id = 1  # first local var at RBP - (8 x 1) = RBP - 8

    # For var in env
    def __contains__(self, item):
        return item in self.local_var_homes

    # env["var name"]
    def __getitem__(self, item):
        if item in self.local_var_homes:
            return self.local_var_homes[item]
        else:
            raise KeyError(f'{item} not found in environment')

    # # env["var name"] = slot_id
    # def __setitem__(self, item, home):
    #     self.local_var_homes[item] = home

    # # del env["var name"]
    # def __delitem__(self, item):
    #     del self.local_var_homes[item]
    #     self.next_avialable_stk_id -= 1

    def add(self, item):
        self.local_var_homes[item] = self.next_avialable_stk_id
        self.next_avialable_stk_id += 1
        #return self.local_var_homes[item]


class Compiler:

    def __init__(self):
        self.init()

    def init(self):
        self.count = 0
        self.ast = None
        self.asm = x86.X86AsmUtils()
        self.main_env =  Environment('main', parent=None)
        self.func_defs = None
        self.use_apx = False

    def gen_sym(self, name):
        self.count += 1
        return name + "_" + str(self.count)

    def compile(self, program, print_ast=True, use_apx=False):
        self.init()
        self.ast = AST.parse(program)
        if print_ast:
            print('#' * 20)
            print(AST.dump(self.ast, indent=4))
            print('#' * 20)

        self.func_defs, self.ast = self.extract_function_defs(self.ast)
        # if print_ast: print(AST.dump(self.ast, indent=4))
        print('*' * 20)
        for f  in self.func_defs:
            print(AST.dump(f, indent=4))
            print('=' * 20)

        self.compile_main()
        if self.func_defs:
            self.compile_functions()
        self.asm.emit_epilogue()
        return self.asm.code

    def extract_function_defs(self, node: AST.AST):
        match node:
            case AST.Module(body):
                func_defs = []
                main_body = []
                for i, ast_node in enumerate(body):
                    if isinstance(ast_node, AST.FunctionDef):
                        func_defs.append(ast_node)
                    else:
                        main_body.append(ast_node)
                return func_defs, AST.Module(body=main_body)
            case _:
                raise LookupError('Unknown AST format')

    def compile_main(self):
        self.asm.emit_header()
        self.compile_ast(node=self.ast, env=self.main_env)
        self.asm.emit_tail()

    def compile_functions(self):
        for fd_ast in self.func_defs:
            fenv = Environment(name=fd_ast.name, parent=self.main_env)
            self.compile_ast(node=fd_ast, env=fenv)

    def compile_ast(self, node: AST.AST, env: Environment):
        compile_ast = self.compile_ast
        asm = self.asm
        gen_sym = self.gen_sym

        match node:
            case AST.Module(body):
                print('Compiling module')
                for stmt in body:
                    compile_ast(stmt, env)

            case AST.Expr(value=v):
                print('Compiling Expr')
                compile_ast(v, env)

            case AST.Constant(value=v):
                print('Compiling Value')
                if type(v) == bool: v = int(v)
                asm.emit_instr(f'mov rax, {v}')

            #------------------- UnaryOp expression -----------------
            case AST.UnaryOp(op=uop, operand=opr):
                print('Compiling UnaryOp')
                compile_ast(opr, env)
                compile_ast(uop, env)

            case AST.USub():
                print('Compiling USub')
                asm.emit_instr('neg rax')

            case AST.Invert():
                print('Compiling Invert/negate')
                asm.emit_instr('not rax')

            case AST.Not():
                print('Compiling logical not')
                asm.emit_code_block('''\
                ; logical not
                cmp rax, 0
                sete al
                movzx rax, al
                ''')

            #------------------- BinaryOp expression -----------------
            case AST.BinOp(opr_left, op, opr_right) \
                | AST.Compare(opr_left, [op], [opr_right]) \
                | AST.BoolOp(op, [opr_left, opr_right]) :
                print('Compiling BinOp')
                compile_ast(opr_left, env)
                # Store opr_left on the stack (temp var)
                stk_offset = -8 * env.next_avialable_stk_id
                env.next_avialable_stk_id += 1
                asm.emit_instr(f'mov [rbp + {stk_offset}], rax')
                compile_ast(opr_right, env)
                # Reuse the stack location created for the temp to store opr_left
                env.next_avialable_stk_id -= 1

                match op:
                    case AST.Add():
                        asm.emit_instr(f'add rax, [rbp + {stk_offset}]')

                    case AST.Sub():
                        if self.use_apx:
                            asm.emit_instr(f'sub rax, [rbp + {stk_offset}], rax')
                        else:
                            asm.emit_instr('neg rax')
                            asm.emit_instr(f'add rax, [rbp + {stk_offset}]')

                    case AST.Mult():
                        asm.emit_instr(f'imul rax, [rbp + {stk_offset}]')

                    case AST.Div() | AST.Mod():
                        asm.emit_code_block(f'''\
                        ; division
                        mov r8, rax ; divisor
                        mov rax, [rbp + {stk_offset}]; dividend
                        ; cqto not working (NASM issue)
                        mov rdx, rax
                        sar rdx, 63
                        idiv r8
                        ''')
                        if isinstance(op, AST.Mod):
                            asm.emit_instr("mov rax, rdx")

                    case AST.Gt() | AST.GtE() | AST.Lt() | AST.LtE() | AST.Eq() | AST.NotEq():
                        cc_map = {AST.Gt : 'g', AST.GtE : 'ge', AST.Lt : 'l',
                                  AST.LtE : 'le', AST.Eq : 'e', AST.NotEq : 'ne'}
                        cc = cc_map[type(op)]
                        asm.emit_code_block(f'''\
                        ; binop compare
                        cmp [rbp + {stk_offset}], rax
                        set{cc} al
                        movzx rax, al
                        ''')

                    case AST.And() | AST.Or() | AST.BitXor() | AST.BitAnd() | AST.BitOr():
                        op_map = {AST.And : 'and', AST.Or : 'or', AST.BitXor : 'xor',
                                  AST.BitAnd : 'and', AST.BitOr : 'or'}
                        operator = op_map[type(op)]
                        asm.emit_instr(f'{operator} rax, [rbp + {stk_offset}]')

                    case AST.RShift() | AST.LShift():
                        op_map = {AST.RShift : 'sar', AST.LShift : 'sal'}
                        operator = op_map[type(op)]
                        # TODO: raise error for negative shift count? C/Java doesn't and returns 0
                        asm.emit_code_block(f'''\
                        ; binop shift
                        mov rcx, rax
                        mov rax, [rbp + {stk_offset}]
                        {operator} rax, cl
                        ''')
                    case _:
                        raise NotImplementedError("Binary op not implemented")


            #------------------- if expression -----------------
            case AST.IfExp(test=if_exp, body=then_exp, orelse=else_exp):
                print('Compiling If Exp')
                compile_ast(if_exp, env)
                asm.emit_instr('cmp rax, 0')
                label_else = gen_sym('ifexp_else')
                asm.emit_instr(f'je {label_else}')
                compile_ast(then_exp, env)
                label_done = gen_sym('ifexp_done')
                asm.emit_instr(f'jmp {label_done}')
                asm.emit_label(f'{label_else}')
                compile_ast(else_exp, env)
                asm.emit_label(f'{label_done}')

            #------------------- Variable binding -----------------
            #case AST.Name(id, AST.Load()): -> also works
            case AST.Name(id):
                print(f'Compiling Name Expr: {id}')
                if id in env:
                    stk_offset = -8 * env[id]
                    asm.emit_instr(f'mov rax, [rbp + {stk_offset }]')
                else:
                    raise LookupError(f'Variable {id} is not assigned')

            #case AST.Assign([AST.Name(id, AST.Store())], value): -> also works
            case AST.Assign([AST.Name(id)], value):
                print('Compiling Single Assign')
                compile_ast(value, env)
                if id not in env:
                    env.add(id)
                stk_offset = -8 * env[id]
                asm.emit_instr(f'mov [rbp + {stk_offset }], rax')

            #------------------- Function definition -----------------
            case AST.FunctionDef(name, args, body):
                print(f'Compiling FunctionDef: {name}')
                self.asm.emit_label(name)
                self.asm.emit_instr('push rbp')
                self.asm.emit_instr('mov rbp, rsp')
                # Map arguments to stack slots
                if args:
                    for idx, arg in enumerate(args.args):
                        self.env[arg.arg] = idx + 1
                for stmt in body:
                    compile_ast(stmt, env)
                # self.asm.emit_instr('leave')
                self.asm.emit_instr('pop rbp')
                self.asm.emit_instr('ret')

            #------------------- Function call -----------------
            case AST.Call(func, args, keywords):
                print(f'Compiling Call: {getattr(func, "id", func)}')
                # Allocate stack space on the caller's frame to save the result of the call
                asm.emit_instr('sub rsp, 8')

                # Evaluate arguments and push them in reverse order
                for arg in reversed(args):
                    compile_ast(arg, env)

                # Call function
                if hasattr(func, 'id'):
                    asm.emit_instr(f'call {func.id}')
                else:
                    raise NotImplementedError('Only simple function calls supported')
                # Pop arguments off the stack
                if args:
                    asm.emit_instr(f'add rsp, {8 * len(args)}')
                # Return value is in rax

            #------------------- Return statement -----------------
            case AST.Return(value):
                print('Compiling Return')
                compile_ast(value, env)
                # asm.emit_instr('ret')

            case unknown:
                raise NotImplementedError(f'language feature not supported for {type(unknown)}')

if __name__ == '__main__':
    asm_code = Compiler().compile(program, print_ast=True)
    import runtime as rt
    rt.run_asm(asm_code, keep_asm=True)
