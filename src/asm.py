import textwrap

class X86AsmUtils:

    def __init__(self):
        self.code = ""

    def emit_header(self):
        self.emit_block('''\
        DEFAULT REL
        SECTION .text
            global _entry
        _entry:
            ; save rbp and setup new stack frame
            push rbp
            mov rbp, rsp
            sub rsp, 8000  ; allocate stack space for 100 local variables
            ; function body starts here
        ''')

    def emit_block(self, blk):
        self.code += textwrap.dedent(blk);

    def emit_code_block(self, cblk):
        self.code += textwrap.indent(textwrap.dedent(cblk), "\t")

    def emit_tail(self):
        self.emit_code_block('''\
        ; exiting
        ;pop rbp
        leave
        ret
        ''')

    def emit_instr(self, instr):
        self.code += f"\t{instr}\n"

    def emit_comment(self, comment, marker='='):
        # Format as ; ----------- <comment> -----------
        dashes = marker * ((60 - len(comment)) // 2)
        self.code += f"\t; {dashes} {comment} {dashes}\n"

    def emit_label(self, label):
        self.code += f"{label}:\n"

    def emit_epilogue(self):
        self.code += 'SECTION .note.GNU-stack noexec'

    def show(self):
        print(self.code)
