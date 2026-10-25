"""Aplicar el parche local solo sobre los tres archivos originales conocidos."""

import argparse
import hashlib
from importlib.util import find_spec
from pathlib import Path
import subprocess


# SHA256 antes y después del parche combinado, sobre el commit documentado.
HASHES = {
    "ghidra_diff_engine.py": (
        "00defe3c6b08babaf37928062554a54b773c49da081728d17e36aaae88ad7ae7",
        "eae71d3fa0e9c4ae6289bc8a618c58cc1582e36a421531208517e35088f317f3",
    ),
    "simple_diff.py": (
        "39d2d11828e688d67b23d430adc5e98894e13a4666ff0127189eac0f0d7e007b",
        "1e5cf05b5743847b4f570ba75608947bc174c530bcd0d5d6bbb2b9da045de4f0",
    ),
    "structural_graph_diff.py": (
        "51ea7e591e1d7310acb67f4d76cb9ee9f582161450b2df9c4aba763cd1d8d80a",
        "58dd825746a542293cbbab368448049e20db781d21c9ef6fb4808c653a889d14",
    ),
}


def main() -> int:
    """Comprobar hashes; aplicar una vez o confirmar que ya está aplicado."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Comprobar sin modificar; 0 si está aplicado")
    args = parser.parse_args()
    spec = find_spec("ghidriff")
    if spec is None or spec.origin is None:
        parser.error("Instala primero requirements.txt en el entorno activo.")
    package = Path(spec.origin).resolve().parent
    actual = {name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in HASHES}
    if all(actual[name] == pair[1] for name, pair in HASHES.items()):
        print(f"Parche de Ghidriff ya aplicado y verificado: {package}")
        return 0
    if not all(actual[name] == pair[0] for name, pair in HASHES.items()):
        parser.error("Los archivos no coinciden con la base ni con el parche completo; no se modifican.")
    if args.check:
        print(f"Base correcta; parche pendiente: {package}")
        return 1
    patch_file = Path(__file__).with_name("ghidriff-local.patch").resolve()
    command = ["patch", "--batch", "--forward", "-p1", "-d", str(package.parent), "-i", str(patch_file)]
    subprocess.run([*command, "--dry-run"], check=True)
    subprocess.run(command, check=True)
    for name, pair in HASHES.items():
        if hashlib.sha256((package / name).read_bytes()).hexdigest() != pair[1]:
            raise RuntimeError(f"El resultado no coincide con el parche esperado: {name}")
    print(f"Parche aplicado y verificado: {package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
