"""Set de herramientas complementarias para el modelo.
    Contiene:
    - get_disassembly(version, address, instruction_count)
    - read_data(version, address)
    - read_memory(version, address, size)
    - list_memory_blocks(version)
    - list_data_items(version, block_name, offset, limit)
    - list_exports(version)
    
"""
from itertools import islice
from typing import Any

from .ghidra_session import Version, session
from .main_set import _resolve_address


def get_disassembly(version: Version, address: str, instruction_count: int) -> list[str]:
    """Obtiene el desensamblado de la dirección especificada en la versión dada."""
    if instruction_count < 1:
        raise ValueError("instruction_count debe ser >= 1")

    program, addr = _resolve_address(version, address)
    listing = program.getListing()
    instructions = listing.getInstructions(addr, True)

    return [instr.toString() for instr in islice(instructions, instruction_count)]


def read_data(version: Version, address: str) -> dict[str, Any]:
    """Consultar el objeto Data completo que contiene address."""
    program, addr = _resolve_address(version, address)

    data = program.getListing().getDataContaining(addr)

    if data is None:
        raise ValueError(f"No hay datos en la dirección: {address}")

    block = program.getMemory().getBlock(addr)

    value = data.getValue()
    return {
        "value": str(value) if value is not None else None,
        "data_type": data.getDataType().getName(),
        "size": data.getLength(),
        "block_name": block.getName() if block is not None else None,
        "block_start": block.getStart().toString() if block is not None else None,
        "block_end": block.getEnd().toString() if block is not None else None,
    }


def read_memory(version: Version, address: str, size: int) -> dict[str, str | int]:
    """Leer size bytes inicializados de Ghidra, como hexadecimal y ASCII."""
    if size < 1:
        raise ValueError("size debe ser >= 1")

    program, addr = _resolve_address(version, address)

    end = addr.addNoWrap(size - 1)
    if not program.getMemory().getAllInitializedAddressSet().contains(addr, end):
        raise ValueError("El rango solicitado contiene memoria inexistente o sin inicializar")

    flat = session.flat_old if version == "old" else session.flat_new
    data = bytes(value & 0xff for value in flat.getBytes(addr, size))
    return {
        "version": version,
        "address": addr.toString(),
        "size": len(data),
        "hex": data.hex(" "),
        "ascii": "".join(chr(value) if 32 <= value <= 126 else "." for value in data),
    }


def list_memory_blocks(version: Version) -> list[dict[str, str | int | bool]]:
    """Lista los bloques de memoria en la versión dada."""
    program = session[version]
    memory = program.getMemory()
    blocks = memory.getBlocks()

    return [
        {
            "name": block.getName(),
            "start": block.getStart().toString(),
            "end": block.getEnd().toString(),
            "size": block.getSize(),
            "is_readable": block.isRead(),
            "is_writable": block.isWrite(),
            "is_executable": block.isExecute(),
            "is_initialized": block.isInitialized(),
        }
        for block in blocks
    ]


def list_data_items(
    version: Version,
    block_name: str = ".rodata",
    offset: int = 0,
    limit: int = 25,
) -> list[dict[str, str | int]]:
    """Lista una página de datos definidos por Ghidra en un bloque."""
    if offset < 0 or limit < 1:
        raise ValueError("offset debe ser >= 0 y limit debe ser >= 1")

    # Las clases Java están disponibles después de abrir la sesión.
    from ghidra.program.model.address import AddressSet # type: ignore

    program = session[version]
    block = program.getMemory().getBlock(block_name)
    if block is None:
        raise ValueError(f"No existe el bloque {block_name!r} en {version}")

    addresses = AddressSet(block.getStart(), block.getEnd())
    defined_data = program.getListing().getDefinedData(addresses, True)

    items = []
    for data in islice(defined_data, offset, offset + limit):
        items.append({
            "address": data.getAddress().toString(),
            "type": data.getDataType().getName(),
            "size": data.getLength(),
            "value_repr": data.getDefaultValueRepresentation(),
        })

    return items


def list_exports(version: Version) -> list[dict[str, str | bool | None]]:
    """Listar puntos de entrada externos, con firma o tipo de dato."""

    program = session[version]
    symbol_table = program.getSymbolTable()
    function_manager = program.getFunctionManager()
    listing = program.getListing()

    exports = []

    for address in symbol_table.getExternalEntryPointIterator():
        symbol = symbol_table.getPrimarySymbol(address)
        function = function_manager.getFunctionAt(address)
        data = listing.getDefinedDataAt(address)

        signature = None
        data_type = None

        if function is not None:
            signature = function.getSignature().getPrototypeString(True)
        elif data is not None:
            data_type = data.getDataType().getName()

        exports.append({
            "version": version,
            "address": address.toString(),
            "name": symbol.getName(True) if symbol is not None else None,
            "symbol_type": (
                symbol.getSymbolType().toString() if symbol is not None else None
            ),
            "is_function": function is not None,
            "signature": signature,
            "data_type": data_type,
        })

    return exports
