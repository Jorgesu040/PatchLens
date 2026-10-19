import json
from copy import deepcopy
from pathlib import Path


OPTIONAL_FUNCTION_FIELDS = {"sig": "sig", "callees": "called", "callers": "calling"}
REQUIRED_FUNCTION_FIELDS = ("name", "address", "code")
CHANGE_FIELDS = ("diff", "match_types")
FUNCTION_GROUPS = ("added", "deleted", "modified")
METADATA_FIELDS = {
    "program_name": "Program Name",
    "sha256": "Executable SHA256",
    "format": "Executable Format",
    "architecture": "Language ID",
    "ghidra_version": "Created With Ghidra Version",
}


def _copy_required(source, fields, warnings, context):
    if not isinstance(source, dict):
        raise TypeError(f"{context} debe ser un objeto JSON")

    for field in fields:
        if field not in source:
            warnings.append(f"Falta el campo obligatorio '{field}' en {context}")
    return deepcopy({field: source.get(field) for field in fields})


def _copy_function(source, warnings, context):
    function = _copy_required(source, REQUIRED_FUNCTION_FIELDS, warnings, context)
    for output, field in OPTIONAL_FUNCTION_FIELDS.items():
        if field in source:
            function[output] = deepcopy(source[field])
    return function


def get_functions(function_data, change_type, json_file, json_path):
    if change_type not in FUNCTION_GROUPS:
        raise ValueError(f"Tipo de cambio desconocido: {change_type}")

    changes = []

    for index, item in enumerate(function_data):
        change = {
            "change_id": f"{change_type}_{index}",
            "change_type": change_type,
            "old_function": None,
            "new_function": None,
            "evidence": {
                "file": str(json_file),
                "json_path": f"{json_path}[{index}]",
            },
            "warnings": [],
        }

        try:
            if change_type == "modified":
                for side, context in (("old", "función anterior"), ("new", "función nueva")):
                    change[f"{side}_function"] = _copy_function(
                        item[side], change["warnings"], context
                    )
                change["change_details"] = _copy_required(
                    item, CHANGE_FIELDS, change["warnings"], "change_details"
                )
            else:
                side, context = {
                    "added": ("new", "función añadida"),
                    "deleted": ("old", "función eliminada"),
                }[change_type]
                change[f"{side}_function"] = _copy_function(
                    item, change["warnings"], context
                )
        except (KeyError, TypeError) as error:
            change["warnings"].append(
                f"Error al procesar {change_type} en el índice {index}: {error}"
            )

        changes.append(change)

    return changes


def get_added(added_data, json_file, json_path='$["functions"]["added"]'):
    return get_functions(added_data, "added", json_file, json_path)


def get_deleted(deleted_data, json_file, json_path='$["functions"]["deleted"]'):
    return get_functions(deleted_data, "deleted", json_file, json_path)


def get_modifications(modified_data, json_file, json_path='$["functions"]["modified"]'):
    return get_functions(modified_data, "modified", json_file, json_path)


def _validate_functions(data):
    if not isinstance(data, dict):
        raise ValueError("El informe debe ser un objeto JSON")
    functions = data.get("functions")
    if not isinstance(functions, dict):
        raise ValueError("La sección obligatoria 'functions' debe ser un objeto JSON")

    for group in FUNCTION_GROUPS:
        if not isinstance(functions.get(group), list):
            raise ValueError(f"La sección 'functions.{group}' debe existir y ser una lista")
    return functions


def _reduce_metadata(metadata):
    if not isinstance(metadata, dict):
        raise ValueError("Los metadatos deben ser un objeto JSON")

    reduced = {}
    for output_field, input_field in METADATA_FIELDS.items():
        value = metadata.get(input_field)
        if output_field == "architecture" and value is None:
            value = metadata.get("Processor")
        reduced[output_field] = deepcopy(value)
    return reduced


def get_changes(data, json_file):
    functions = _validate_functions(data)
    symbols = data.get("symbols", {})
    strings = data.get("strings", {})

    return {
        "source_file": str(json_file),
        "metadata": {
            "old": _reduce_metadata(data.get("old_meta", {})),
            "new": _reduce_metadata(data.get("new_meta", {})),
        },
        "functions": {
            "added": get_added(functions["added"], json_file),
            "deleted": get_deleted(functions["deleted"], json_file),
            "modified": get_modifications(functions["modified"], json_file),
        },
        "analysis": {
            "stats": deepcopy(data.get("stats", {})),
            "symbols": {
                "added": deepcopy(symbols.get("added", [])),
                "deleted": deepcopy(symbols.get("deleted", [])),
            },
            "strings": {
                "added": deepcopy(strings.get("added", [])),
                "deleted": deepcopy(strings.get("deleted", [])),
            },
        },
    }


def parse_json(json_file):
    json_path = Path(json_file)
    with json_path.open("r", encoding="utf-8") as file:
        return get_changes(json.load(file), json_path)


def main(json_file="data.json", output_file=None):
    result = parse_json(json_file)
    serialized = json.dumps(result, indent=4, ensure_ascii=False)

    if output_file is None:
        print(serialized)
    else:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized, encoding="utf-8")

    return result


__all__ = [
    "get_added",
    "get_deleted",
    "get_modifications",
    "get_changes",
    "parse_json",
    "main",
]


if __name__ == "__main__":
    main()
