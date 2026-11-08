#!/usr/bin/env python3
"""Build CDROP.COM: regenerate tables, assemble with NASM."""
import pathlib, subprocess, sys
root = pathlib.Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(root / "tools" / "gentables.py")], check=True)
subprocess.run(["nasm", "-f", "bin", "-I", str(root / "src") + "/", str(root / "src" / "cdrop.asm"),
                "-o", str(root / "CDROP.COM")], check=True)
print(f"CDROP.COM: {(root / 'CDROP.COM').stat().st_size} bytes")
