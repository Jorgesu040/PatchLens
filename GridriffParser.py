"""Leer informes Ghidriff y coordinar su conversión al formato de PatchLens.

Este módulo conoce los archivos y campos de Ghidriff. NormalizerEngine crea
propuestas comunes, agrupa las equivalentes y detecta las contradictorias.
Una propuesta representa lo que afirma un motor.
"""
import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from parser.NormalizerEngine import find_conflicts, merge_changes, normalize_record, link_conflicts


OPTIONAL_FUNCTION_FIELDS = ("sig", "called", "calling", "refcount", "length")
REQUIRED_FUNCTION_FIELDS = ("name", "address", "code")
FUNCTION_GROUPS = ("added", "deleted", "modified")
ENGINES = ("VersionTrackingDiff", "SimpleDiff", "StructualGraphDiff")
METADATA_FIELDS = {
    "name": "Program Name",
    "sha256": "Executable SHA256",
    "format": "Executable Format",
    "architecture": "Language ID",
    "ghidra_version": "Created With Ghidra Version",
}


def _copy_function(source: dict[str, Any]) -> dict[str, Any]:
    """Copiar los campos de una función que el parser conserva.

    Recibe una función exportada por Ghidriff.

    Devuelve name/address/code y los opcionales presentes con sus nombres
    originales: sig, called (funciones a las que llama) y calling (funciones
    que la llaman), refcount y length.

    Se usa en get_functions para reducir los datos enviados a etapas posteriores.
    No modifica source; si falta un campo obligatorio, propaga KeyError.
    """
    function = {field: deepcopy(source[field]) for field in REQUIRED_FUNCTION_FIELDS}
    for field in OPTIONAL_FUNCTION_FIELDS:
        if field in source:
            function[field] = deepcopy(source[field])
    return function


def get_functions(
    function_data: list[dict[str, Any]],
    change_type: str,
    engine: str,
) -> list[dict[str, Any]]:
    """Convertir un grupo de un motor en una lista de propuestas normalizadas.

    'function_data' es functions[change_type] del JSON original. En added/deleted
    sus elementos son funciones; en modified contienen old, new y diff_type.
    'engine' identifica el análisis de origen. El índice se conserva en json_path.
    Para cada elemento usa normalize_record, selecciona campos con _copy_function
    y conserva el diff disponible en su fuente. No agrupa ni asigna IDs finales.
    Devuelve copias; normalize_record valida change_type para cada registro.
    """
    changes = []
    for index, item in enumerate(function_data):
        change = normalize_record(change_type, item, engine, index)
        for side in ("old_function", "new_function"):
            if change[side] is not None:
                change[side] = _copy_function(change[side])
        if "diff" in item:
            change["sources"][0]["diff"] = deepcopy(item["diff"])
        changes.append(change)
    return changes


def _reduce_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Seleccionar y renombrar metadatos de una versión del binario.

    Recibe old_meta o new_meta y devuelve name, sha256, format, architecture
    y ghidra_version. Si falta Language ID, usa Processor para architecture;
    otros datos ausentes quedan como None. parse_json usa el resultado para
    identificar las versiones.
    """
    reduced = {output: metadata.get(field) for output, field in METADATA_FIELDS.items()}
    if reduced["architecture"] is None:
        reduced["architecture"] = metadata.get("Processor")
    return reduced


def get_changes(data: dict[str, Any], engine: str) -> list[dict[str, Any]]:
    """Recoger todas las propuestas de un informe en una lista plana.

    Recibe el JSON original y el identificador de su motor. Recorre added,
    deleted y modified mediante get_functions, en ese orden; cada propuesta
    conserva su campo type. La lista permite recorrer todos los tipos juntos
    para agrupar propuestas y buscar conflictos entre motores posteriormente.
    No fusiona propuestas, no resuelve discrepancias ni modifica data.
    """
    changes = []
    for kind in FUNCTION_GROUPS:
        changes.extend(get_functions(data["functions"][kind], kind, engine))
    return changes


def parse_json(json_file: str | Path, engine: str) -> dict[str, Any]:
    """Leer y adaptar el informe original de un único motor.

    json_file es la ruta al JSON de Ghidriff; engine identifica sus fuentes.
    Devuelve binaries (old/new), analysis (ruta absoluta y estadísticas)
    y changes (lista de get_changes). Es el paso de lectura de parse_reports,
    no el resultado multimotor final. No ejecuta Ghidra ni fusiona informes.
    Exige hashes no vacíos; fallos de lectura o campos necesarios se propagan.
    """
    path = Path(json_file).resolve()
    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    binaries = {}
    for side in ("old", "new"):
        binaries[side] = _reduce_metadata(data[f"{side}_meta"])
        if not binaries[side]["sha256"]:
            raise ValueError(f"Falta SHA256 {side} en {path}")

    return {
        "binaries": binaries,
        "analysis": {"report": str(path), "stats": data["stats"]},
        "changes": get_changes(data, engine),
    }


def parse_reports(reports: dict[str, str | Path]) -> dict[str, Any]:
    """Coordinar la lectura y fusión de uno o varios informes de motores.

    reports relaciona identificador de motor con ruta a su JSON original.
    Lee cada informe con parse_json y exige que coincidan los hashes old/new.
    Después acumula propuestas, usa merge_changes y find_conflicts y enlaza IDs.
    Devuelve schema_version, binaries, analyses, changes y conflicts.
    Conserva propuestas incompatibles para su revisión; no elige por mayoría.
    Rechaza entrada vacía, motor desconocido o hashes incompatibles. No ejecuta
    los motores: Main los ejecuta y entrega aquí las rutas de sus resultados.
    """
    if not reports:
        raise ValueError("Se necesita al menos un informe")

    all_changes: list[dict[str, Any]] = []
    analyses: dict[str, Any] = {}
    binaries: dict[str, Any] | None = None

    for engine, filename in reports.items():
        if engine not in ENGINES:
            raise ValueError(f"Motor desconocido: {engine}")
        report = parse_json(filename, engine)
        if binaries is None:
            binaries = report["binaries"]
        else:
            for side in ("old", "new"):
                if binaries[side]["sha256"] != report["binaries"][side]["sha256"]:
                    raise ValueError(f"Informe incompatible {engine}: SHA256 {side} no coincide")
        analyses[engine] = report["analysis"]
        all_changes.extend(report["changes"])

    changes = merge_changes(all_changes)
    conflicts = find_conflicts(changes)
    link_conflicts(changes, conflicts)
    return {
        "schema_version": "2.0",
        "binaries": binaries,
        "analyses": analyses,
        "changes": changes,
        "conflicts": conflicts,
    }


def main() -> None:
    """Ejecutar el parser desde terminal sobre informes ya generados.

    Lee --report ENGINE=JSON (repetible) y --output, llama a parse_reports
    y escribe el JSON conjunto. Rechaza motores repetidos y sobrescribir un
    informe de entrada. Crea el directorio de salida si hace falta y devuelve
    None. Es distinto de Main.py: aquí no se comparan binarios con Ghidriff.
    """
    cli = argparse.ArgumentParser(description="Normalizar informes Ghidriff ya generados")
    cli.add_argument("--report", action="append", required=True, metavar="ENGINE=JSON")
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()

    reports = {}
    for report in args.report:
        engine, separator, filename = report.partition("=")
        if not separator or not filename:
            cli.error("Cada informe debe indicarse como ENGINE=JSON")
        if engine in reports:
            cli.error(f"Motor repetido: {engine}")
        reports[engine] = filename
    if args.output.resolve() in {Path(value).resolve() for value in reports.values()}:
        cli.error("La salida no puede sobrescribir un informe original")

    result = parse_reports(reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"JSON multimotor: {args.output}")


if __name__ == "__main__":
    main()
