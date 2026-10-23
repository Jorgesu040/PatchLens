"""Set de herramientas complementarias para el modelo.
    Contiene:
    - get_disassembly(version, address, instruction_count)
    - read_data(version, address, size)
    - list_segments(version)
    - list_data_items(version, offset, limit)
    
"""

from ghidra_session import session, Version

def get_disassembly(version: Version, address: str, instruction_count: int):
    """Obtiene el desensamblado de la dirección especificada en la versión dada."""

    program = session[version]
