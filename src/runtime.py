import subprocess
import os

def run_asm(nasm_code, filename="program", keep_asm=False):

    # Write NASM code to a file
    with open(f"{filename}.asm", "w") as f:
        f.write(nasm_code)

    # Assemble the NASM code, runtime.c and link them
    subprocess.run(["nasm", "-felf64", f"{filename}.asm"], check=True)
    subprocess.run(["gcc", "-o", f"{filename}", f"{filename}.o", "runtime.c"], check=True)

    # Execute the code
    result = subprocess.run(["./program"], capture_output=True, text=True, check=True)

    print(result.stdout)

    # Clean up files
    if not keep_asm: os.remove(f"{filename}.asm")
    os.remove(f"{filename}.o")
    os.remove(f"{filename}")