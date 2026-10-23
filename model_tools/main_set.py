"""Set principal de herramientas para el modelo. 
    Contiene:
    - get_binary_info(version)
    - list_functions(version, offset, limit)
    - get_function(version, address)
    - get_function_by_name(version, query)
    - search_functions_by_name(version, query)
    - get_function_calls(version, address, direction)
    - get_references(version, address, direction, offset, limit, include_noise, follow_thunks)
    - list_strings(version, offset, limit)
    - search_strings(version, query)
    - list_imports(version)
"""

from itertools import islice
from typing import Any, Literal

import argparse

from .ghidra_session import Version, session

def _resolve_address(version: Version, address: str) -> tuple[Any, Any]:
    """Devolver los objetos Java (Program, Address); fallar si versión o dirección no son válidas."""
    if version not in ("old", "new"):
        raise ValueError("version debe ser 'old' o 'new'")

    program = session[version]
    addr = program.getAddressFactory().getAddress(address)

    if addr is None:
        raise ValueError(f"Dirección no válida: {address}")

    return program, addr


def get_binary_info(version: Version) -> dict[str, str | int | None]:
    """Devolver metadatos y desglosar funciones totales, no externas y externas."""
    program = session[version]
    manager = program.getFunctionManager()
    total = manager.getFunctionCount()
    external_count = sum(1 for _ in manager.getExternalFunctions())
    return {
        "name": program.getName(),
        "executable_format": program.getExecutableFormat(),
        "language_id": program.getLanguageID().getIdAsString(),
        "compiler_spec_id": program.getCompilerSpec().getCompilerSpecID().getIdAsString(),
        "image_base": program.getImageBase().toString(),
        "sha256": program.getExecutableSHA256(),
        "function_count": total,
        "non_external_function_count": total - external_count,
        "external_function_count": external_count,
    }

def list_functions(version: Version, offset: int = 0, limit: int = 10) -> dict[str, Any]:
    """Paginar funciones no externas con total, returned, has_more e indicador de thunk."""
    program = session[version]
    functions = list(program.getFunctionManager().getFunctions(True))

    func_list = []

    for func in islice(functions, offset, offset + limit):
        func_list.append({
            "name": func.getName(),
            "function_address": func.getEntryPoint().toString(),
            "signature": func.getSignature().getPrototypeString(True),
            "is_thunk": func.isThunk(),
        })

    return {
        "scope": "non_external",
        "total": len(functions),
        "offset": offset,
        "returned": len(func_list),
        "has_more": offset + len(func_list) < len(functions),
        "functions": func_list,
    }


def get_function(version: Version, address: str) -> dict[str, Any]:
    """Obtener pseudocódigo con opciones de Ghidriff, firma, parámetros y callers/callees."""
    program, address_obj = _resolve_address(version, address)
    function_at_address = program.getFunctionManager().getFunctionAt(address_obj)

    if function_at_address is None:
        raise ValueError(f"No se encontró función en la dirección {address}")

    from ghidra.app.decompiler import DecompInterface, DecompileOptions  # pyright: ignore[reportMissingImports]
    from ghidra.util.task import ConsoleTaskMonitor  # pyright: ignore[reportMissingImports]

    decomp = DecompInterface()
    try:
        # Igual que GhidraDiffEngine.setup_decompliers; reutilizar el análisis guardado.
        options = DecompileOptions()
        options.grabFromProgram(program)
        options.setMaxPayloadMBytes(100)
        decomp.setOptions(options)
        if not decomp.openProgram(program):
            raise RuntimeError(decomp.getLastMessage())

        results = decomp.decompileFunction(function_at_address, 60, ConsoleTaskMonitor())

        if not results.decompileCompleted():
            raise RuntimeError(results.getErrorMessage())

        decompiled = results.getDecompiledFunction()
        if decompiled is None:
            raise RuntimeError("Descompilación sin representación C")

        parametros = [{
            "name": p.getName(),
            "type": p.getDataType().getName(),
            "storage": p.getVariableStorage().toString(),
        } for p in function_at_address.getParameters()]

        calling_convention = function_at_address.getCallingConventionName()

        return {
            "version": version,
            "function_address": function_at_address.getEntryPoint().toString(),
            "name": function_at_address.getName(),
            "calling_convention": calling_convention if calling_convention is not None else None,
            "signature": function_at_address.getSignature().getPrototypeString(True),
            "parameters": parametros,
            "pseudocode": decompiled.getC(),
            "warnings": results.getErrorMessage(),
            "callers": get_function_calls(version, address, "callers"),
            "callees": get_function_calls(version, address, "callees"),
        }
    finally:
        decomp.dispose()


def get_function_by_name(version: Version, query: str) -> dict[str, Any]:
    """Consultar la primera función global con nombre exacto; fallar si no existe."""
    program = session.flat_new if version == "new" else session.flat_old
    functions = program.getGlobalFunctions(query)

    if not functions:
        raise ValueError(f"No se encontró ninguna función con el nombre '{query}'")

    function = functions[0]
    return get_function(version, function.getEntryPoint().toString())


def search_functions_by_name(
    version: Version, query: str, fuzzy_threshold: float = 50
) -> list[dict[str, str | float]]:
    """Buscar nombres con similitud mayor que el umbral (0–100); fallar sin coincidencias."""
    program = session[version]
    functions = list(program.getFunctionManager().getFunctions(True))

    from rapidfuzz import fuzz

    matches = []

    for func in functions:
        score = fuzz.ratio(func.getName(), query)
        if score > fuzzy_threshold:  # Umbral de similitud
            matches.append({
                "name": func.getName(),
                "function_address": func.getEntryPoint().toString(),
                "signature": func.getSignature().getPrototypeString(True),
                "similarity_score": score,
            })

    if not matches:
        raise ValueError(
            f"No se encontraron funciones similares a '{query}' con un umbral de {fuzzy_threshold}."
        )

    return matches


def get_function_calls(
    version: Version, address: str, direction: Literal["callers", "callees"]
) -> list[dict[str, str | bool]]:
    """Listar callers o callees de la función que contiene address, ordenados por dirección."""
    if direction not in ("callers", "callees"):
        raise ValueError("direction debe ser 'callers' o 'callees'")

    program, addr = _resolve_address(version, address)
    function = program.getFunctionManager().getFunctionContaining(addr)

    if function is None:
        raise ValueError(f"No hay una función que contenga {address}")

    functions = (
        function.getCallingFunctions(None)
        if direction == "callers"
        else function.getCalledFunctions(None)
    )

    results = [
        {
            "name": f.getName(),
            "entry_point": f.getEntryPoint().toString(),
            "is_external": f.isExternal(),
            "is_thunk": f.isThunk(),
        }
        for f in functions
    ]

    # Sort by entry point
    return sorted(results, key=lambda item: item["entry_point"])


def _function_info(function) -> dict[str, Any] | None:
    """Identificar una función sin descompilarla."""
    if function is None:
        return None
    return {
        "name": function.getName(True),
        "address": function.getEntryPoint().toString(),
        "is_external": function.isExternal(),
        "is_thunk": function.isThunk(),
    }


def _references_to(program, address, follow_thunks):
    """Recorrer referencias al destino exacto y, opcionalmente, a sus thunks."""
    addresses = [address]
    function = program.getFunctionManager().getFunctionAt(address)
    if follow_thunks and function is not None:
        target = function.getThunkedFunction(True) or function
        addresses += [target.getEntryPoint(), *(target.getFunctionThunkAddresses(True) or [])]
    for target in dict.fromkeys(addresses):
        yield from program.getReferenceManager().getReferencesTo(target)


def get_references(
    version: Version, address: str, direction: Literal["to", "from"] = "to",
    offset: int = 0, limit: int = 50, include_noise: bool = False, follow_thunks: bool = False,
) -> dict[str, Any]:
    """Paginar referencias de una dirección exacta; from consulta solo esa instrucción.

    include_noise conserva pila y fallthrough. En to, follow_thunks amplía la
    consulta a los thunks del destino; en ambos sentidos añade destinos resueltos.
    total cuenta las referencias después de filtrar, antes de paginar.
    """
    if direction not in ("to", "from"):
        raise ValueError("Dirección inválida. Use 'to' o 'from'.")

    program, address_obj = _resolve_address(version, address)
    manager = program.getReferenceManager()
    references = (
        _references_to(program, address_obj, follow_thunks)
        if direction == "to"
        else manager.getReferencesFrom(address_obj)
    )

    references = [
        ref for ref in references
        if include_noise or not (ref.getReferenceType().isFallthrough() or ref.isStackReference())
    ]

    functions = program.getFunctionManager()
    rows = []
    for ref in references[offset:offset + limit]:
        source, target = ref.getFromAddress(), ref.getToAddress()
        target_function = functions.getFunctionAt(target) or functions.getFunctionContaining(target)
        resolved = None
        if follow_thunks and target_function is not None and target_function.isThunk():
            resolved = target_function.getThunkedFunction(True)
        symbol = program.getSymbolTable().getPrimarySymbol(target)
        rows.append({
            "from_address": source.toString(),
            "to_address": target.toString(),
            "operand_index": ref.getOperandIndex(),
            "reference_type": ref.getReferenceType().toString(),
            "from_function": _function_info(functions.getFunctionContaining(source)),
            "to_function": _function_info(target_function),
            "to_label": symbol.getName(True) if symbol is not None else None,
            "resolved_to_function": _function_info(resolved),
        })

    return {
        "version": version,
        "address": address_obj.toString(),
        "direction": direction,
        "include_noise": include_noise,
        "follow_thunks": follow_thunks,
        "offset": offset,
        "total": len(references),
        "returned": len(rows),
        "has_more": offset + len(rows) < len(references),
        "references": rows,
    }


def list_strings(version: Version, offset: int = 0, limit: int = 10) -> list[dict[str, str | int]]:
    """Paginar cadenas reconocidas por Ghidra; fallar si no hay ninguna en el programa."""
    program = session[version]

    types = program.getListing().getDefinedData(True)

    from ghidra.program.model.data import StringDataInstance  # pyright: ignore[reportMissingImports]

    strings = [ StringDataInstance.getStringDataInstance(data) for data in types if StringDataInstance.isString(data)]

    if not strings:
        raise ValueError("No se encontraron cadenas en el binario.")

    return [
        {
            "string": data.getStringValue(),
            "address": data.getAddress().toString(),
            "length": data.getStringLength(),
            "has_more": offset + limit < len(strings),
        }
        for data in islice(strings, offset, offset + limit)
    ]


# TODO?: implementar fuzzy search en la misma o en otra función?
def search_strings(version: Version, query: str) -> list[dict[str, str | int]]:
    """Filtrar cadenas por subcadena sin distinguir mayúsculas; fallar si no hay cadenas."""
    program = session[version]
    types = program.getListing().getDefinedData(True)

    from ghidra.program.model.data import StringDataInstance  # pyright: ignore[reportMissingImports]

    strings = [ StringDataInstance.getStringDataInstance(data) for data in types if StringDataInstance.isString(data)]

    if not strings:
        raise ValueError("No se encontraron cadenas en el binario.")

    return [
        {
            "string": data.getStringValue(),
            "address": data.getAddress().toString(),
            "length": data.getStringLength(),
        }
        for data in strings
        if query.lower() in data.getStringValue().lower()
    ]

def list_imports(version: Version) -> dict[str, list[dict[str, str | bool | None]]]:
    """Agrupar símbolos externos por módulo, con firma o tipo de dato.

    ExternalSpaceAddress pertenece al espacio EXTERNAL de Ghidra, no es una
    dirección de ejecución. Firma y tipo reflejan lo conocido por el análisis.
    """
    program = session[version]
    manager = program.getExternalManager()
    imports = {}

    # Obtener todos los módulos externos
    for module in manager.getExternalLibraryNames():
        symbols = []

        # Para cada símbolo externo en el módulo, obtener su firma o tipo de dato
        for location in manager.getExternalLocations(module):
            is_function = location.isFunction()
            signature = None
            data_type = None

            if is_function:
                function = location.getFunction()
                signature = function.getSignature().getPrototypeString(True)
            else:
                datatype = location.getDataType()
                if datatype is not None:
                    data_type = datatype.getName()

            symbols.append({
                "label": location.getLabel(),
                "isFunction": is_function,
                "ExternalSpaceAddress": location.getExternalSpaceAddress().toString(),
                "signature": signature,
                "data_type": data_type,
            })

        # Agrupar símbolos por módulo
        imports[module] = symbols

    return imports


def main() -> None:
    """Comprobar la conexión: python -m model_tools.main_set --help."""
    parser = argparse.ArgumentParser(description="Abrir las versiones old/new en Ghidra.")
    parser.add_argument("--project", required=True, help="Ruta al archivo .gpr")
    parser.add_argument("--program-old", required=True, help="Ruta interna de la versión antigua")
    parser.add_argument("--program-new", required=True, help="Ruta interna de la versión nueva")
    parser.add_argument("--ghidra-install", help="Instalación de Ghidra; por defecto GHIDRA_INSTALL_DIR")
    args = parser.parse_args()

    session.open(
        args.project, args.program_old, args.program_new, args.ghidra_install
    )
    try:
        for version in ("old", "new"):
            program = session[version]
            print(
                f"{version}: {program.getName()} | "
                f"SHA256: {program.getExecutableSHA256()} | "
                f"Funciones: {program.getFunctionManager().getFunctionCount()}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
