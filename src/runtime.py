import subprocess
import os
from pathlib import Path

def run_asm(nasm_code, filename="program", use_apx=False, keep_asm=True):

    # Write NASM code to a file
    with open(f"{filename}.asm", "w") as f:
        f.write(nasm_code)

    # Assemble the NASM code, runtime.c and link them
    subprocess.run(["/usr/local/bin/nasm", "-felf64", f"{filename}.asm"], check=True)
    script_dir = Path(__file__).resolve().parent
    c_file_path = script_dir / 'runtime.c'
    subprocess.run(["gcc", "-o", f"{filename}", f"{filename}.o", str(c_file_path)], check=True)

    # Execute the code
    if not use_apx:
        result = subprocess.run(["./program"], capture_output=True, text=True, check=True)
    else:
        result = subprocess.run(["/home/parasa/tools/sde957/sde64", "-dmr", "--", "./program"], capture_output=True, text=True, check=True)


    print(result.stdout)

    # Clean up files
    if not keep_asm: os.remove(f"{filename}.asm")
    os.remove(f"{filename}.o")
    #os.remove(f"{filename}")
    return result.stdout