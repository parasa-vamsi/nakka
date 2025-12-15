import ast as AST
import src.asm as x86

# Keep this formatting to avoid IndentationError
program = \
"""
144 // 12

"""

class Environment:

    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.local_var_homes = dict()
        self.func_arg_homes = dict()
        self.use_registers = True
        self.next_avialable_stk_id = 1  # first local var at RBP - (8 x 1) = RBP - 8
        # Use a deterministic ordered list of available registers (prefer callee-saved first)
        self.available_registers = ['rbx', 'r12', 'r13', 'r14', 'r15', 'r10', 'r11', 'r9', 'r8', 'rdi', 'rsi']
        self.restricted_registers = {'rax', 'rbp', 'rsp', 'rdx', 'rcx'}
        self.occupied_registers = set()
        self.register_arguments = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9'] # don't change the order!
        self.caller_save_registers = ['rax'] + self.register_arguments + ['r10', 'r11']
        self.callee_save_registers = ['rbx', 'rbp', 'rsp', 'r12', 'r13', 'r14', 'r15']
    
    @property
    def num_register_arguments(self):
        return len(self.register_arguments)
    
    # For var in env
    def __contains__(self, item):
        return item in self.local_var_homes or item in self.func_arg_homes

    # env["var name"]
    def __getitem__(self, item):
        if item in self.local_var_homes:
            var_home = self.local_var_homes[item]
            multiplier = -8 # local variables grow downwards below rbp (callee frame)
        elif item in self.func_arg_homes:
            var_home = self.func_arg_homes[item]
            multiplier = +8 # function arguments are above rbp in the caller's frame
        else:
            raise KeyError(f'{item} not found in environment')
        
        if isinstance(var_home, str): # register
                return var_home
        else:
            stk_offset = multiplier * var_home
            return f'[rbp + {stk_offset}]'

    # env["var name"] = slot_id ONLY for function arguments
    def __setitem__(self, item, home):
        if item in self.local_var_homes:
            raise NotImplementedError(f'Cannot directly assign local variable {item} home; use add() method instead')
        
        self.func_arg_homes[item] = home
        if isinstance(home, str): # register
            self.occupied_registers.add(home)
            if home in self.available_registers:
                self.available_registers.remove(home)

    # del env["var name"] only for local variables
    def __delitem__(self, item):
        var_home = self.local_var_homes[item]
        if self.use_registers and var_home in self.occupied_registers:
            self.occupied_registers.remove(var_home)
            # return the register to the available pool at the end
            self.available_registers.append(var_home)
        else:
            self.next_avialable_stk_id -= 1
        del self.local_var_homes[item]

    # add a new local variable
    def add(self, item):
        if self.use_registers and self.available_registers:
            # allocate from the end for stack-like behavior
            self.local_var_homes[item] = self.available_registers.pop()
            self.occupied_registers.add(self.local_var_homes[item])
        else:
            self.local_var_homes[item] = self.next_avialable_stk_id
            self.next_avialable_stk_id += 1
        return self.__getitem__(item)

    def is_register(self, item_home):
        return True if item_home[0] == 'r' else False


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
                asm.emit_comment(f'load constant {v}')
                asm.emit_instr(f'mov rax, {v}')

            #------------------- UnaryOp expression -----------------
            case AST.UnaryOp(op=uop, operand=opr):
                print('Compiling UnaryOp')
                compile_ast(opr, env)
                compile_ast(uop, env)

            case AST.USub():
                print('Compiling USub')
                asm.emit_comment('unary negate')
                asm.emit_instr('neg rax')

            case AST.Invert():
                print('Compiling Invert/negate')
                asm.emit_comment('bitwise invert')
                asm.emit_instr('not rax')

            case AST.Not():
                print('Compiling logical not')
                asm.emit_comment('logical not')
                asm.emit_code_block('''\
                cmp rax, 0
                sete al
                movzx rax, al
                ''')

            #------------------- BinaryOp expression -----------------
            case AST.BinOp(opr_left, op, opr_right) \
                | AST.Compare(opr_left, [op], [opr_right]) \
                | AST.BoolOp(op, [opr_left, opr_right]) :
                print('Compiling BinOp')
                asm.emit_comment(f'binary op: {type(op).__name__}')
                compile_ast(opr_right, env)
                # Store opr_right as a temp var
                temp_var = gen_sym('.temp')
                opr_right_home = env.add(temp_var)
                asm.emit_instr(f'mov {opr_right_home}, rax')
                compile_ast(opr_left, env) # opr_left will be in rax
                # Reuse the temp var home created for the temp to store opr_right
                del env[temp_var]

                match op:
                    case AST.Add():
                        asm.emit_instr(f'add rax, {opr_right_home}')

                    case AST.Sub():
                        if self.use_apx:
                            asm.emit_instr(f'sub rax, rax, {opr_right_home}')
                        else:
                            asm.emit_instr(f'sub rax, {opr_right_home}')

                    case AST.Mult():
                        asm.emit_instr(f'imul rax, {opr_right_home}')

                    case AST.FloorDiv() | AST.Mod(): # AST.Div() deprecated to enable automated testing
                        SIZE = '' if env.is_register(opr_right_home) else 'QWORD'
                        asm.emit_code_block(f'''\
                        ; division (cqto has issues)
                        mov rdx, rax ; dividend
                        sar rdx, 63
                        idiv {SIZE} {opr_right_home}
                        ''')
                        if isinstance(op, AST.Mod):
                            asm.emit_instr("mov rax, rdx")

                    case AST.Gt() | AST.GtE() | AST.Lt() | AST.LtE() | AST.Eq() | AST.NotEq():
                        cc_map = {AST.Gt : 'g', AST.GtE : 'ge', AST.Lt : 'l',
                                  AST.LtE : 'le', AST.Eq : 'e', AST.NotEq : 'ne'}
                        cc = cc_map[type(op)]
                        asm.emit_code_block(f'''\
                        ; binop compare
                        cmp rax, {opr_right_home}
                        set{cc} al
                        movzx rax, al
                        ''')

                    case AST.And() | AST.Or() | AST.BitXor() | AST.BitAnd() | AST.BitOr():
                        op_map = {AST.And : 'and', AST.Or : 'or', AST.BitXor : 'xor',
                                  AST.BitAnd : 'and', AST.BitOr : 'or'}
                        operator = op_map[type(op)]
                        asm.emit_instr(f'{operator} rax, {opr_right_home}')

                    case AST.RShift() | AST.LShift():
                        op_map = {AST.RShift : 'sar', AST.LShift : 'sal'}
                        operator = op_map[type(op)]
                        # TODO: raise error for negative shift count? C/Java doesn't and returns 0
                        asm.emit_code_block(f'''\
                        ; binop shift
                        mov rcx, {opr_right_home}
                        {operator} rax, cl
                        ''')
                    case _:
                        raise NotImplementedError("Binary op not implemented")


            #------------------- if expression -----------------
            case AST.IfExp(test=if_exp, body=then_exp, orelse=else_exp):
                print('Compiling If Exp')
                asm.emit_comment('if-expression')
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
                asm.emit_comment(f'load variable {id}')
                if id in env:
                    var_home = env[id]
                    asm.emit_instr(f'mov rax, {var_home}')
                else:
                    raise LookupError(f'Variable {id} is not assigned')

            #case AST.Assign([AST.Name(id, AST.Store())], value): -> also works
            case AST.Assign([AST.Name(id)], value):
                print('Compiling Single Assign')
                asm.emit_comment(f'assign to {id}')
                compile_ast(value, env)
                if id not in env:
                    env.add(id)
                var_home = env[id]
                asm.emit_instr(f'mov {var_home}, rax')

            # Functions compilation
            # Notes: https://course.ccs.neu.edu/cs4410sp24/lec_function-calls_notes.html

            #------------------- Function definition -----------------
            case AST.FunctionDef(name, arguments, body):
                print(f'Compiling FunctionDef: {name}')
                self.asm.emit_label(name)
                asm.emit_comment(f'function: {name}', marker='*')
                self.asm.emit_instr('push rbp')
                self.asm.emit_instr('mov rbp, rsp')
                self.asm.emit_instr('sub rsp, 8000  ; 100 local variables') # allocate stack space for local variables

                # push callee save registers
                asm.emit_comment('Push callee-save registers', marker='-')
                for reg in env.callee_save_registers:
                    if reg != 'rbp' and reg != 'rsp': # leave instr takes care of rbp and rsp
                        self.asm.emit_instr(f'push {reg}')

                # Map arguments to environnment slots
                for idx, arg in enumerate(arguments.args):
                    if idx < env.num_register_arguments:
                        env[arg.arg] = env.register_arguments[idx]
                    else:
                        env[arg.arg] = (idx - env.num_register_arguments) + 2  # +2 to account for return address and old rbp

                print(env.local_var_homes)

                # Compile function body
                asm.emit_comment('Compile function body', marker='-')
                for stmt in body:
                    compile_ast(stmt, env)

                # pop callee save registers
                asm.emit_comment('Pop callee-save registers', marker='-')
                for reg in reversed(env.callee_save_registers):
                    if reg != 'rbp' and reg != 'rsp':
                        self.asm.emit_instr(f'pop {reg}')

                self.asm.emit_instr('leave')
                self.asm.emit_instr('ret')

            #------------------- Function call -----------------
            case AST.Call(func, arguments, keywords):
                print(f'Compiling Call: {getattr(func, "id", func)}')
                asm.emit_comment(f'call {getattr(func, "id", func)}', marker='*')

                # Save only the occupied caller-save registers before we clobber them
                # These hold local variable values that must be preserved across the call
                asm.emit_comment('Push occupied caller-save registers', marker='-')
                occupied_caller_saves = [reg for reg in env.caller_save_registers 
                                        if reg in env.occupied_registers and reg != 'rax']
                for reg in occupied_caller_saves:
                    asm.emit_instr(f'push {reg}')

                asm.emit_comment('Prepare function arguments', marker='-')
                # Prepare stack arguments (indices 6+) by pushing them in reverse order
                for idx in range(len(arguments) - 1, env.num_register_arguments - 1, -1):
                    asm.emit_comment('Evaluate stack argument', marker='-')
                    compile_ast(arguments[idx], env)  # value in rax
                    asm.emit_instr(f'push rax')

                # Prepare register arguments (indices 0-5).
                # To avoid clobbering sources that may live in registers, we
                # first evaluate each register argument and push its value
                # onto the stack (left-to-right). Then pop them into the
                # appropriate argument registers in reverse order.
                max_reg_idx = min(env.num_register_arguments - 1, len(arguments) - 1)
                # evaluate and push temps
                for idx in range(max_reg_idx + 1):
                    asm.emit_comment('Evaluate register argument', marker='-')
                    compile_ast(arguments[idx], env)  # value in rax
                    asm.emit_instr('push rax')
                # pop into argument registers (high->low)
                asm.emit_comment('Move arguments from stack to registers', marker='-')
                for idx in range(max_reg_idx, -1, -1):
                    arg_dst = env.register_arguments[idx]
                    asm.emit_instr(f'pop {arg_dst}')

                # Call function
                if hasattr(func, 'id'):
                    asm.emit_comment('Call the function', marker='*')
                    asm.emit_comment(f'Registers in use before call: {env.occupied_registers}')
                    asm.emit_instr(f'call {func.id}')
                else:
                    raise NotImplementedError('Only simple function calls supported')
                # Pop arguments off the stack
                if len(arguments) > env.num_register_arguments:
                    asm.emit_comment('Pop the stack allocated arguments', marker='-')
                    num_stack_args = len(arguments) - env.num_register_arguments
                    asm.emit_instr(f'add rsp, {8 * num_stack_args}')

                # Pop occupied caller-save registers from the stack (in reverse order)
                asm.emit_comment('Pop the caller-save registers', marker='-')
                for reg in reversed(occupied_caller_saves):
                    asm.emit_instr(f'pop {reg}')
                asm.emit_comment('End of function call compilation', marker='*')

            #------------------- Return statement -----------------
            case AST.Return(value):
                print('Compiling Return')
                asm.emit_comment('return')
                compile_ast(value, env)

            case unknown:
                raise NotImplementedError(f'language feature not supported for {type(unknown)}')

if __name__ == '__main__':
    asm_code = Compiler().compile(program, print_ast=True)
    import runtime as rt
    rt.run_asm(asm_code, keep_asm=True)
