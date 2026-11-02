"""Funciones complementarias para Responses, con todos los argumentos explícitos.

Fuente: https://developers.openai.com/api/docs/guides/function-calling
Strict exige required para todas las propiedades y additionalProperties=False.
Los defaults Python se indican en las descripciones; no se acepta null.
"""

tools_schemas = [
    {
        "type": "function",
        "name": "get_disassembly",
        "description": (
            "Consultar instrucciones de ensamblador desde una dirección, en orden ascendente. "
            "Devuelve hasta instruction_count instrucciones como texto. Puede avanzar a "
            "otras funciones o bloques; no está limitado al cuerpo de una función."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "enum": ["old", "new"]},
                "address": {
                    "type": "string",
                    "description": "Dirección Ghidra; conservar su espacio de direcciones si aparece.",
                },
                "instruction_count": {"type": "integer", "minimum": 1},
            },
            "required": ["version", "address", "instruction_count"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "read_data",
        "description": (
            "Consultar el objeto Data de Ghidra que contiene la dirección. Devuelve "
            "su valor textual o null, tipo, tamaño completo y bloque de memoria. "
            "Puede incluir datos sin definir. Falla si no hay un objeto Data "
            "(por ejemplo, en una instrucción). No lee un rango de bytes."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "enum": ["old", "new"]},
                "address": {"type": "string", "description": "Dirección Ghidra dentro del dato."},
            },
            "required": ["version", "address"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "read_memory",
        "description": (
            "Leer size bytes desde una dirección de la memoria del programa en Ghidra. "
            "Devuelve versión, dirección, tamaño, hexadecimal y ASCII "
            "(punto para bytes no imprimibles). Falla si el rango incluye memoria "
            "inexistente o sin inicializar; propaga errores de acceso a memoria. "
            "Permite leer código y datos sin definir. "
            "No consulta la memoria de un proceso en ejecución."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "enum": ["old", "new"]},
                "address": {"type": "string", "description": "Dirección Ghidra de inicio de la lectura."},
                "size": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Número de bytes que se quieren leer.",
                },
            },
            "required": ["version", "address", "size"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_memory_blocks",
        "description": (
            "Listar los bloques de memoria de una versión. Cada bloque contiene name, "
            "start, end, size (número de bytes), is_readable, is_writable, "
            "is_executable e is_initialized. Consultar antes de elegir el bloque "
            "para list_data_items; los nombres dependen del binario."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"version": {"type": "string", "enum": ["old", "new"]}},
            "required": ["version"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_data_items",
        "description": (
            "Paginar los datos definidos por Ghidra en un bloque por orden de dirección. "
            "Devuelve dirección, tipo, tamaño y representación textual del valor. "
            "No incluye bytes sin definir. Falla si no existe el bloque."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "enum": ["old", "new"]},
                "block_name": {
                    "type": "string",
                    "description": "Nombre exacto obtenido de list_memory_blocks. Default Python: .rodata.",
                },
                "offset": {
                    "type": "integer", "minimum": 0,
                    "description": "Datos que se omiten, no bytes. Primera página: 0.",
                },
                "limit": {
                    "type": "integer", "minimum": 1,
                    "description": "Máximo de datos por página. Default Python: 25.",
                },
            },
            "required": ["version", "block_name", "offset", "limit"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_exports",
        "description": (
            "Listar los puntos de entrada externos de Ghidra en una versión. Devuelve "
            "dirección, nombre y tipo de símbolo, indicador de función y firma o tipo "
            "de dato si se conocen. Son puntos exportados, no importaciones; "
            "para dependencias externas usar list_imports."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"version": {"type": "string", "enum": ["old", "new"]}},
            "required": ["version"],
            "additionalProperties": False,
        },
    },
]
