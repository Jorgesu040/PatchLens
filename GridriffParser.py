import json
from copy import deepcopy
from pathlib import Path


FUNCTION_FIELDS = ("name", "address", "code", "sig")
FUNCTION_RELATIONSHIPS = (("callees", "called"), ("callers", "calling"))
REQUIRED_FUNCTION_FIELDS = ("name", "address", "code")
CHANGE_FIELDS = ("diff", "match_types")
REQUIRED_CHANGE_FIELDS = ("diff", "match_types")
FUNCTION_GROUPS = ("added", "deleted", "modified")
METADATA_FIELDS = {
    "program_name": "Program Name",
    "sha256": "Executable SHA256",
    "format": "Executable Format",
    "architecture": "Language ID",
    "ghidra_version": "Created With Ghidra Version",
}


def _copy_function(source, warnings, context):
    if not isinstance(source, dict):
        raise TypeError(f"{context} debe ser un objeto JSON")

    function = {}
    for field in FUNCTION_FIELDS:
        if field in source:
            function[field] = deepcopy(source[field])
        elif field in REQUIRED_FUNCTION_FIELDS:
            function[field] = None
            warnings.append(f"Falta el campo obligatorio '{field}' en {context}")

    for output_field, input_field in FUNCTION_RELATIONSHIPS:
        if input_field in source:
            function[output_field] = deepcopy(source[input_field])

    return function


def _copy_change_details(source, warnings):
    details = {}
    for field in CHANGE_FIELDS:
        if field in source:
            details[field] = deepcopy(source[field])
        elif field in REQUIRED_CHANGE_FIELDS:
            details[field] = None
            warnings.append(f"Falta el campo obligatorio '{field}' en change_details")
    return details


def get_functions(function_data, change_type, json_file, json_path):
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
            if change_type == "added":
                change["new_function"] = _copy_function(
                    item, change["warnings"], "función añadida"
                )
            elif change_type == "deleted":
                change["old_function"] = _copy_function(
                    item, change["warnings"], "función eliminada"
                )
            elif change_type == "modified":
                change["old_function"] = _copy_function(
                    item["old"], change["warnings"], "función anterior"
                )
                change["new_function"] = _copy_function(
                    item["new"], change["warnings"], "función nueva"
                )
                change["change_details"] = _copy_change_details(
                    item, change["warnings"]
                )
            else:
                raise ValueError(f"Tipo de cambio desconocido: {change_type}")
        except (KeyError, TypeError, ValueError) as error:
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
    if "functions" not in data:
        raise ValueError("El informe no contiene la sección obligatoria 'functions'")

    functions = data["functions"]
    if not isinstance(functions, dict):
        raise ValueError("La sección 'functions' debe ser un objeto JSON")

    missing_groups = [group for group in FUNCTION_GROUPS if group not in functions]
    if missing_groups:
        raise ValueError(
            f"La sección 'functions' no contiene: {', '.join(missing_groups)}"
        )

    invalid_groups = [
        group for group in FUNCTION_GROUPS if not isinstance(functions[group], list)
    ]
    if invalid_groups:
        raise ValueError(
            f"Las secciones de funciones deben ser listas: {', '.join(invalid_groups)}"
        )
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