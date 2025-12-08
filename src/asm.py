import textwrap

class X86AsmUtils:

    def __init__(self):
        self.code = ""

    def emit_header(self):
        self.emit_block("""\
        DEFAULT REL
        SECTION .text
            global _entry
        _entry:
            ; save rbp and setup new stack frame
            push rbp
            mov rbp, rsp
            ; function body starts here
        """)

    def emit_block(self, blk):
        self.code += textwrap.dedent(blk);

    def emit_code_block(self, cblk):
        self.code += textwrap.indent(textwrap.dedent(cblk), "\t")

    def emit_tail(self):
        self.emit_block("""\
            ; exiting
            pop rbp
            ret

        SECTION .note.GNU-stack noexec
        """)

    def emit_instr(self, instr):
        self.code += f"\t{instr}\n"

    def emit_label(self, label):
        self.code += f"{label}:\n"

    def show(self):
        print(self.code)
