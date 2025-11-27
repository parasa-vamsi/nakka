class X86AsmUtils:

    def __init__(self):
        self.code = ""

    def emit_header(self):
        self.code += "DEFAULT REL" + "\n"
        self.code += "SECTION .text" + "\n"
        self.code += "\t \t" + "global _entry" + "\n"
        self.emit_label("_entry")

    def emit_tail(self):
        self.code += "\t \t" + "ret" + "\n\n" + "section .note.GNU-stack noexec"

    def emit_instr(self, instr):
        self.code += "\t \t" + f"{instr}" + "\n"

    def emit_label(self, label):
        self.code += f"{label}:" + "\n"

    def show(self):
        print(self.code)
