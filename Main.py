import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from GridriffParser import parse_json


def run_ghidriff(old_binary, new_binary, project_name):
    old_path = Path(old_binary).resolve()
    new_path = Path(new_binary).resolve()
    output_dir = Path("resultados") / project_name
    output_dir.mkdir(parents=True, exist_ok=True)
    ghidriff = shutil.which("ghidriff")

    if ghidriff is None:
        venv_ghidriff = Path(sys.executable).parent / "ghidriff"
        workspace_ghidriff = Path(__file__).resolve().parent.parent / ".venv-ghidriff/bin/ghidriff"
        ghidriff = next(
            (str(candidate) for candidate in (venv_ghidriff, workspace_ghidriff) if candidate.is_file()),
            None,
        )

    if ghidriff is None:
        raise FileNotFoundError(
            "No se encontró el ejecutable ghidriff. Activa el entorno .venv-ghidriff."
        )

    subprocess.run(
        [
            ghidriff,
            str(old_path),
            str(new_path),
            "-o", str(output_dir),
            "--sxs",
            "--bsim-full",
            "--md-title", f"PatchLens-{old_path.stem}-vs-{new_path.stem}.md",
            "--project-name", project_name,
        ],
        check=True,
    )

    return output_dir


def find_report(output_dir, old_binary, new_binary):
    old_name = Path(old_binary).stem
    new_name = Path(new_binary).stem
    expected_report = Path(output_dir) / "json" / f"{old_name}-{new_name}.ghidriff.json"

    if expected_report.is_file():
        return expected_report

    reports = sorted(Path(output_dir).rglob("*.ghidriff.json"))
    if len(reports) == 1:
        return reports[0]
    if not reports:
        raise FileNotFoundError(
            f"No se encontró el informe esperado {expected_report}"
        )
    raise RuntimeError(
        f"Hay varios informes en {output_dir} y falta el esperado {expected_report}"
    )


def main():
    parser = argparse.ArgumentParser(description="Ejecuta ghidriff y parsea su resultado.")
    parser.add_argument("old", type=Path, help="Ruta al binario antiguo")
    parser.add_argument("new", type=Path, help="Ruta al binario nuevo")
    parser.add_argument("--project-name", required=True, help="Nombre del proyecto y del JSON de salida")
    args = parser.parse_args()

    output_dir = run_ghidriff(args.old, args.new, args.project_name)
    report = find_report(output_dir, args.old, args.new)
    result = parse_json(report)

    parsed_output = Path("resultados") / f"{args.project_name}.json"
    parsed_output.write_text(
        json.dumps(result, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Informe procesado: {report}")
    print(f"JSON normalizado: {parsed_output}")

    return result


if __name__ == "__main__":
    main()