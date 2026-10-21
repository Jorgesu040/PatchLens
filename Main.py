import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from GridriffParser import ENGINES, parse_reports


def run_ghidriff(old_binary, new_binary, project_name, engine="VersionTrackingDiff", timeout=300):
    old_path = Path(old_binary).resolve()
    new_path = Path(new_binary).resolve()
    for path in (old_path, new_path):
        if not path.is_file():
            raise FileNotFoundError(f"No existe el binario: {path}")
    if engine not in ENGINES:
        raise ValueError(f"Motor desconocido: {engine}")
    if timeout <= 0:
        raise ValueError("El tiempo límite debe ser positivo")
    ghidriff = shutil.which("ghidriff")

    if ghidriff is None:
        venv_ghidriff = Path(sys.executable).parent / "ghidriff"
        workspace_ghidriff = Path(__file__).resolve().parent.parent / ".venv-ghidriff/bin/ghidriff"
        ghidriff = next(
            (str(candidate) for candidate in (venv_ghidriff, workspace_ghidriff) if candidate.is_file()),
            None,
        )

    output_root = Path("resultados") / project_name
    output_root.mkdir(parents=True, exist_ok=True)
    output_dir = Path(tempfile.mkdtemp(prefix=f"{engine}-", dir=output_root)).resolve()

    if ghidriff is None:
        raise FileNotFoundError(
            "No se encontró el ejecutable ghidriff. Activa el entorno .venv-ghidriff."
        )

    subprocess.run(
        [
            ghidriff,
            str(old_path),
            str(new_path),
            "--engine", engine,
            "-o", str(output_dir),
            "--sxs",
            "--bsim-full",
            "--md-title", f"PatchLens-{old_path.stem}-vs-{new_path.stem}.md",
            "--project-name", project_name,
        ],
        check=True,
        timeout=timeout,
    )

    return output_dir


def find_report(output_dir, old_binary, new_binary):
    old_name = Path(old_binary).stem
    new_name = Path(new_binary).stem
    expected_report = Path(output_dir) / "json" / f"{old_name}-{new_name}.ghidriff.json"

    if expected_report.is_file():
        return expected_report

    raise FileNotFoundError(f"No se encontró el informe esperado {expected_report}")


def main():
    parser = argparse.ArgumentParser(description="Compara binarios con varios motores y normaliza sus resultados.")
    parser.add_argument("old", type=Path, help="Ruta al binario antiguo")
    parser.add_argument("new", type=Path, help="Ruta al binario nuevo")
    parser.add_argument("--project-name", required=True, help="Nombre del proyecto y del JSON de salida")
    parser.add_argument("--engines", nargs="+", choices=ENGINES, default=list(ENGINES))
    parser.add_argument("--timeout", type=int, default=1800, help="Segundos máximos por motor")
    args = parser.parse_args()

    if len(set(args.engines)) != len(args.engines):
        parser.error("Se han encontrado valores repetidos en --engines")
    if args.timeout <= 0:
        parser.error("--timeout debe ser positivo")
    reports = {}
    for engine in args.engines:
        print(f"Analizando con {engine}...", flush=True)
        output_dir = run_ghidriff(args.old, args.new, args.project_name, engine, args.timeout)
        reports[engine] = find_report(output_dir, args.old, args.new)

    # Flujo de salida normalizado para todos los motores
    result = parse_reports(reports)

    parsed_output = Path("resultados") / f"{args.project_name}.json"
    parsed_output.write_text(
        json.dumps(result, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    
    print(f"Motores procesados: {', '.join(reports)}")
    print(f"Cambios agrupados: {len(result['changes'])}; alertas: {len(result['conflicts'])}")
    print(f"JSON normalizado: {parsed_output}")

    return result


if __name__ == "__main__":
    main()