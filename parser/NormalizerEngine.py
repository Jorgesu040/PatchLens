"""Normalizar, agrupar y contrastar propuestas de cambio de distintos motores.

No lee archivos ni ejecuta Ghidra. Trabaja con diccionarios en memoria de UN
par de binarios cuyos hashes ha comprobado el parser. Una función puede estar
implicada en varias propuestas: agrupar coincidencias no elimina discrepancias.
"""

import copy
from typing import Any


# Identidad local de función: (old/new, dirección) dentro del mismo par binario.
FunctionKey = tuple[str, str]

# Identidad de propuesta: (tipo, función antigua o None, función nueva o None).
ChangeKey = tuple[
    str,
    FunctionKey | None,
    FunctionKey | None,
]


# Identifica una función del binario
def function_key(
        version: str,
        function: dict[str, Any] | None,
    ) -> FunctionKey | None:
    """Obtener la identidad de una función en una de las dos versiones.

    Recibe version old/new y un diccionario de función o None. Devuelve
    (version, address), o None cuando ese lado no existe (añadidas/eliminadas).
    Se usa para claves de agrupación e índices de conflictos: no compara código
    ni demuestra correspondencia entre versiones. Solo vale dentro del mismo
    par binario. Valida version incluso con None; versión o dirección inválida
    producen ValueError. normalize_record también la usa para validar sus lados.
    """

    if version not in ('old', 'new'):
        raise ValueError(f"Versión inválida: {version}")
    
    if function is None:
        return None

    address = function.get('address')

    if not isinstance(address, str) or not address:
        raise ValueError(f"Dirección inválida: {address}")

    return (version, address)


    
def normalize_record(
    kind: str,
    raw: dict[str, Any],
    analysis_id: str,
    index: int,
) -> dict[str, Any]:
    """Convertir un registro de un motor en una propuesta de estructura común.

    kind es added/deleted/modified; raw es una función en los dos primeros casos
    o un registro con old/new/diff_type en el tercero. analysis_id identifica el
    análisis; index es la posición dentro de functions[kind] del original.
    Devuelve type, aspects, old_function, new_function y una fuente con procedencia.
    Added tiene solo lado new; deleted solo old; modified ambos. aspects contiene
    existence para añadidas/eliminadas o las etiquetas diff_type para modified.
    Crea copias, sin reducir campos, fusionar ni asignar IDs. El parser selecciona
    campos después. Tipo desconocido o dirección inválida producen ValueError.
    Se asume match_types como lista del Ghidriff parcheado, o campo ausente;
    no se adaptan strings de informes anteriores.
    """
    if kind not in ("added", "deleted", "modified"):
        raise ValueError(f"Tipo inválido: {kind}")

    old_function: dict[str, Any] | None
    new_function: dict[str, Any] | None
    aspects: list[str]

    if kind == "added":
        old_function = None
        new_function = raw
        aspects = ["existence"]
    elif kind == "deleted":
        old_function = raw
        new_function = None
        aspects = ["existence"]
    else:
        old_function = raw["old"]
        new_function = raw["new"]
        aspects = copy.deepcopy(raw["diff_type"])

    function_key("old", old_function)
    function_key("new", new_function)

    source: dict[str, Any] = {
        "analysis": analysis_id,
        "json_path": f"$.functions.{kind}[{index}]",
        "aspects": copy.deepcopy(aspects),
        "match_types": list(dict.fromkeys(raw.get("match_types", []))),
    }

    return {
        "type": kind,
        "aspects": aspects,
        "old_function": copy.deepcopy(old_function),
        "new_function": copy.deepcopy(new_function),
        "sources": [source],
    }
    
# Identifica una propuesta de modificación / 
def change_key(
    change: dict[str, Any],
) -> ChangeKey:
    """Obtener la clave con la que merge_changes agrupa una propuesta.

    Recibe un cambio normalizado y devuelve (tipo, identidad old, identidad new).
    El motor y el nombre no forman parte de la clave: varios motores pueden
    proponer el mismo cambio. Added y modified de la misma función nueva NO
    comparten clave y deben conservarse para detectar el conflicto posterior.
    Los matches, sin type, usan el tipo interno match para agrupar sus parejas.
    No es un hash del pseudocódigo ni un ID global; no modifica la propuesta.
    """

    change_type = change.get("type", "match")

    old_identity = function_key("old", change.get("old_function"))

    new_identity = function_key("new", change.get("new_function"))

    return (change_type, old_identity, new_identity)



def merge_changes(
    changes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Agrupar propuestas equivalentes conservando evidencia de cada fuente.

    Recibe cambios o matches normalizados de uno o varios motores; los matches
    tienen old_function/new_function y sources, sin type ni aspects.
    Agrupa por change_key y devuelve copias en orden de primera aparición.
    Une aspects sin duplicados y conserva sources distintas; solo elimina
    fuentes totalmente iguales, no rutas distintas del mismo motor.
    Los aspectos de cada fuente explican qué detectó ese motor; los del cambio
    resumen su unión. Las exportaciones de old_function y new_function deben
    coincidir dentro del grupo; si difieren, lanza ValueError en lugar de guardar
    variantes o elegir una silenciosamente. No compara old contra new.
    No modifica entradas, no resuelve conflictos ni convierte apoyos en confianza.
    """
    grouped: dict[ChangeKey, dict[str, Any]] = {}

    for change in changes:
        key = change_key(change)

        if key not in grouped:
            grouped[key] = copy.deepcopy(change)
            continue

        existing = grouped[key]

        if (
            existing["old_function"] != change["old_function"]
            or existing["new_function"] != change["new_function"]
        ):
            raise ValueError(f"Exportaciones distintas para la misma propuesta: {key}")

        if "aspects" in existing:
            existing["aspects"] = list(
                dict.fromkeys(existing["aspects"] + change["aspects"])
            )

        for source in change["sources"]:
            source = copy.deepcopy(source)
            if source not in existing["sources"]:
                existing["sources"].append(source)

    return list(grouped.values())


def find_conflicts(
    changes: list[dict[str, Any]],
    matches=(),
) -> list[dict[str, Any]]:
    """Detectar propuestas incompatibles sobre las mismas identidades de función.

    Recibe cambios y matches ya fusionados, con lados válidos. Indexa las
    funciones old/new para buscar added_vs_modified, deleted_vs_modified,
    added_modified_deleted, same_old_to_multiple_new y multiple_old_to_same_new.
    Devuelve alertas con tipo, funciones y change_indices/match_indices: posiciones
    en cada lista, no IDs. link_conflicts convierte esos índices en enlaces públicos.
    Las correspondencias ambiguas se revisan juntas, sin duplicar alertas.
    No modifica entradas ni decide qué propuesta es correcta. Added y deleted
    sin una correspondencia modificada entre ellos no son un conflicto por sí
    solos. Una ausencia en un motor tampoco se interpreta como contradicción.
    """
    records = [*changes, *matches]
    changes_by_old_function: dict[FunctionKey, dict[str, list[int]]] = {}
    changes_by_new_function: dict[FunctionKey, dict[str, list[int]]] = {}

    modified_changes: list[int] = []
    classification_conflict_types = {
        (True, False): "added_vs_modified",
        (False, True): "deleted_vs_modified",
        (True, True): "added_modified_deleted",
    }

    # 1. Agrupar los índices según las funciones a las que afectan.
    for change_index, change in enumerate(records):
        kind = change.get("type", "match")

        old_function_key = function_key("old", change["old_function"])
        new_function_key = function_key("new", change["new_function"])

        if kind == "modified":
            modified_changes.append(change_index)

        if old_function_key is not None:
            related_changes = changes_by_old_function.setdefault(
                old_function_key, {"deleted": [], "modified": [], "match": []}
            )
            related_changes[kind].append(change_index)

        if new_function_key is not None:
            related_changes = changes_by_new_function.setdefault(
                new_function_key, {"added": [], "modified": [], "match": []}
            )
            related_changes[kind].append(change_index)

    conflicts: list[dict[str, Any]] = []

    # 2. Revisar discrepancias de clasificación alrededor de cada modificación.
    for modified_index in modified_changes:
        # Los registros ya han sido normalizados por el parser.
        change = changes[modified_index]
        old_function_key = ("old", change["old_function"]["address"])
        new_function_key = ("new", change["new_function"]["address"])
        deleted_indices = changes_by_old_function[old_function_key]["deleted"]
        added_indices = changes_by_new_function[new_function_key]["added"]

        conflict_type = classification_conflict_types.get(
            (bool(added_indices), bool(deleted_indices))
        )

        if conflict_type is not None:
            conflicts.append({
                "type": conflict_type,
                "old_function": old_function_key,
                "new_function": new_function_key,
                "change_indices": added_indices + deleted_indices + [modified_index],
            })

    # 3. Buscar una función antigua relacionada con varias nuevas.
    for old_function_key, related_changes in changes_by_old_function.items():
        pair_indices = related_changes["modified"] + related_changes["match"]

        new_function_keys = {
            function_key("new", records[index]["new_function"])
            for index in pair_indices
        }

        if len(new_function_keys) > 1:
            conflicts.append({
                "type": "same_old_to_multiple_new",
                "old_function": old_function_key,
                "change_indices": pair_indices,
            })

    # 4. Buscar varias funciones antiguas relacionadas con una misma nueva.
    for new_function_key, related_changes in changes_by_new_function.items():
        pair_indices = related_changes["modified"] + related_changes["match"]

        old_function_keys = {
            function_key("old", records[index]["old_function"])
            for index in pair_indices
        }

        if len(old_function_keys) > 1:
            conflicts.append({
                "type": "multiple_old_to_same_new",
                "new_function": new_function_key,
                "change_indices": pair_indices,
            })

    for conflict in conflicts:
        indices = conflict["change_indices"]
        conflict["change_indices"] = [index for index in indices if index < len(changes)]
        conflict["match_indices"] = [index - len(changes) for index in indices if index >= len(changes)]
    return conflicts


def link_conflicts(changes: list[dict[str, Any]], conflicts: list[dict[str, Any]], matches=()) -> None:
    """Asignar IDs finales y enlazar cambios, matches y conflictos en ambos sentidos.

    Recibe cambios ya fusionados y conflictos de find_conflicts cuyos
    change_indices apuntan a esa lista. Modifica ambas listas in situ:
    inicializa change_id/match_id/conflict_ids y conflict_id/change_ids/match_ids; retira los índices
    internos de cada conflicto, dejando solo enlaces por ID. Devuelve None.
    Se usa después de la fusión para que registros agrupados compartan un ID.
    Los IDs dependen del orden; no son hashes ni identificadores globales.
    """
    for kind, records in (("change", changes), ("match", matches)):
        for index, record in enumerate(records):
            record[f"{kind}_id"] = f"{kind}_{index:04d}"
            record["conflict_ids"] = []

    for index, conflict in enumerate(conflicts):
        conflict["conflict_id"] = f"conflict_{index:04d}"
        for kind, records in (("change", changes), ("match", matches)):
            conflict[f"{kind}_ids"] = []
            for record_index in conflict.pop(f"{kind}_indices"):
                record = records[record_index]
                conflict[f"{kind}_ids"].append(record[f"{kind}_id"])
                record["conflict_ids"].append(conflict["conflict_id"])

