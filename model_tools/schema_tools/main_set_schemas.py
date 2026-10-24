"""Schemas de las consultas de main_set para la API Responses.

En modo strict se requieren todos los argumentos: los defaults de Python se
indican en las descripciones para que el modelo los envíe de forma explícita.
No se admite null, porque las funciones actuales no lo interpretan como default.

Fuente: https://developers.openai.com/api/docs/guides/function-calling?api-mode=responses#defining-functions
"""

tools_schemas = [
    {
        "type": "function",
        "name": "get_binary_info",
        "description": (
            "Consultar los metadatos de una versión antes de investigar sus funciones. "
            "Devuelve nombre, formato ejecutable, identificador de lenguaje/arquitectura, "
            "especificación de compilador, dirección base, SHA-256 y número de funciones "
            "conocidas por Ghidra: function_count es el total, "
            "non_external_function_count cuenta las no externas y "
            "external_function_count las externas. El total de list_functions corresponde "
            "a non_external_function_count, no a function_count."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "enum": ["old", "new"],
                    "description": "Versión del programa: old para la anterior y new para la nueva.",
                },
            },
            "required": ["version"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "list_functions",
        "description": (
            "Listar funciones no externas de una versión por orden de dirección. "
            "Devuelve scope, total de funciones no externas, offset, returned, "
            "has_more y functions con nombre, dirección de inicio, firma e is_thunk. "
            "Usar offset y limit para paginar; consultar list_imports para los "
            "símbolos externos. Incluye thunks en ram aunque su bloque se llame EXTERNAL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "enum": ["old", "new"],
                    "description": "Versión del programa: old para la anterior y new para la nueva.",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "description": (
                        "Número de funciones que se saltan, no bytes. "
                        "Usar 0 para la primera página."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Número máximo de funciones que se devuelven. Valor por defecto: 10.",
                },
            },
            "required": ["version", "offset", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_function",
        "description": (
            "Obtener versión, dirección, nombre, convención de llamada, firma, parámetros, "
            "pseudocódigo, avisos y listas de callers/callees "
            "de una función por su dirección de inicio exacta en la versión indicada. "
            "No acepta una dirección interior de la función. El pseudocódigo usa "
            "las opciones del programa y la configuración de descompilación de Ghidriff. "
            "Puede ser incompleto; no es el código fuente original."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "enum": ["old", "new"],
                    "description": "Versión del programa: old para la anterior y new para la nueva.",
                },
                "address": {
                    "type": "string",
                    "description": (
                        "Dirección de inicio exacta tal como la devuelve Ghidra, "
                        "por ejemplo 001011e7. Conservar el espacio de direcciones "
                        "si aparece; no convertirla a entero."
                    ),
                },
            },
            "required": ["version", "address"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_function_by_name",
        "description": (
            "Obtener firma, parámetros, pseudocódigo, avisos y listas de callers/callees de la primera función "
            "global cuyo nombre coincide exactamente con query en la versión indicada. "
            "Falla si no existe en el espacio global, aunque aparezca en otro namespace. "
            "Para consultar una función de otro namespace, usar get_function con su dirección. "
            "Para explorar nombres similares, usar "
            "search_functions_by_name. El pseudocódigo usa las opciones del programa "
            "y la configuración de descompilación de Ghidriff; puede ser incompleto "
            "y no es el código fuente original."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "enum": ["old", "new"],
                    "description": "Versión del programa: old para la anterior y new para la nueva.",
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Nombre global exacto de la función, por ejemplo calcular_envio. "
                        "No es una búsqueda aproximada ni devuelve todas las coincidencias."
                    ),
                },
            },
            "required": ["version", "query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_functions_by_name",
        "description": (
            "Buscar funciones no externas por similitud textual entre su nombre y query, "
            "distinguiendo mayúsculas. Devuelve nombre, dirección, firma y "
            "puntuación de similitud; mantiene el orden por dirección. "
            "Produce un error si no encuentra coincidencias."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "enum": ["old", "new"],
                    "description": "Versión del programa: old para la anterior y new para la nueva.",
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Texto que se compara con los nombres de las funciones; "
                        "no interpreta patrones ni expresiones regulares."
                    ),
                },
                "fuzzy_threshold": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": (
                        "Umbral de similitud: solo admite puntuaciones estrictamente "
                        "mayores. Valor por defecto: 50. Un umbral de 100 no devuelve "
                        "coincidencias, ni siquiera nombres idénticos."
                    ),
                },
            },
            "required": ["version", "query", "fuzzy_threshold"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_function_calls",
        "description": (
            "Listar las funciones que llaman a la función que contiene la dirección "
            "indicada, o las funciones a las que esta llama, según Ghidra. Devuelve "
            "nombre, entry_point, is_external e is_thunk, ordenados por dirección. "
            "Cada función aparece una vez, aunque existan varias llamadas; no devuelve "
            "las instrucciones de llamada ni recorre cadenas de thunks. Falla si la "
            "dirección no pertenece a una función."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "enum": ["old", "new"],
                    "description": "Versión del programa: old para la anterior y new para la nueva.",
                },
                "address": {
                    "type": "string",
                    "description": (
                        "Dirección de Ghidra situada dentro de la función que se quiere "
                        "consultar. Conservar el formato y el espacio de direcciones "
                        "devueltos por las herramientas."
                    ),
                },
                "direction": {
                    "type": "string",
                    "enum": ["callers", "callees"],
                    "description": (
                        "callers devuelve las funciones que llaman a esta función; "
                        "callees devuelve las funciones a las que esta llama."
                    ),
                },
            },
            "required": ["version", "address", "direction"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_references",
        "description": (
            "Paginar referencias entrantes o salientes de una dirección exacta de Ghidra. "
            "from consulta solo la instrucción indicada, no el cuerpo de la función. "
            "Devuelve references con direcciones originales, operand_index, reference_type, "
            "from_function, to_function, to_label y resolved_to_function al resolver un thunk. "
            "Los contextos o etiquetas desconocidos son null. La respuesta incluye "
            "version, scope=address, address, direction, include_noise, follow_thunks, "
            "offset, total, returned, has_more y references. total cuenta referencias "
            "filtradas antes de paginar; continuar con offset mientras has_more. "
            "Una página vacía no produce un error."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "enum": ["old", "new"],
                    "description": "Versión del programa: old para la anterior y new para la nueva.",
                },
                "address": {
                    "type": "string",
                    "description": (
                        "Dirección exacta de Ghidra cuyas referencias se quieren "
                        "consultar. Conservar el formato y el espacio de direcciones "
                        "devueltos por las herramientas."
                    ),
                },
                "direction": {
                    "type": "string",
                    "enum": ["to", "from"],
                    "description": (
                        "to devuelve referencias que llegan a la dirección y es la "
                        "opción habitual para localizar sus usos; from devuelve "
                        "referencias que salen de ella. Valor por defecto: to."
                    ),
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Referencias filtradas que se omiten al paginar. Valor inicial: 0.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Máximo de referencias de la página. Valor por defecto: 50.",
                },
                "include_noise": {
                    "type": "boolean",
                    "description": "false (por defecto) excluye pila y fallthrough; true los incluye.",
                },
                "follow_thunks": {
                    "type": "boolean",
                    "description": (
                        "Valor por defecto: false. Con true, las entrantes a una función "
                        "incluyen sus thunks y el destino final; las salientes conservan "
                        "sus direcciones y añaden resolved_to_function si procede."
                    ),
                },
            },
            "required": ["version", "address", "direction", "offset", "limit", "include_noise", "follow_thunks"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "list_strings",
        "description": (
            "Listar una página de las cadenas definidas y reconocidas por Ghidra "
            "en una versión del programa. Devuelve una lista con string, address, length "
            "y has_more en cada elemento; no devuelve un total ni un objeto envoltorio. "
            "Si has_more es true, continuar con offset + limit. "
            "Puede incluir cadenas de tablas de símbolos; address identifica el "
            "espacio de direcciones de Ghidra y no siempre una dirección de ejecución. "
            "Lanza un error si el programa no contiene cadenas reconocidas. "
            "Una página sin resultados devuelve una lista vacía."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "enum": ["old", "new"],
                    "description": "Versión del programa: old para la anterior y new para la nueva.",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "description": (
                        "Número de cadenas que se omiten antes de devolver la página. "
                        "Usar 0 para empezar."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Número máximo de cadenas que se devuelven. Valor por defecto: 10.",
                },
            },
            "required": ["version", "offset", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_strings",
        "description": (
            "Buscar una subcadena literal sin distinguir mayúsculas y minúsculas "
            "entre las cadenas definidas y reconocidas por Ghidra en una versión "
            "del programa. Devuelve todas las coincidencias con string, address y "
            "length, sin paginación. Puede incluir cadenas de tablas de símbolos; "
            "address identifica el espacio de direcciones de Ghidra y no siempre "
            "una dirección de ejecución. Devuelve una lista vacía si no hay "
            "coincidencias y lanza un error si el programa no contiene cadenas "
            "reconocidas. No admite expresiones regulares."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "enum": ["old", "new"],
                    "description": "Versión del programa: old para la anterior y new para la nueva.",
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Subcadena literal que se busca dentro del texto de cada "
                        "cadena. Una consulta vacía coincide con todas las cadenas."
                    ),
                },
            },
            "required": ["version", "query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "list_imports",
        "description": (
            "Consultar los símbolos externos conocidos para investigar llamadas "
            "y dependencias de una versión. Los agrupa por el módulo asignado por "
            "Ghidra y devuelve label, isFunction, ExternalSpaceAddress, signature y data_type. "
            "signature se usa para funciones y data_type para otros símbolos; "
            "los valores no disponibles son null. Puede devolver módulos "
            "vacíos o un grupo '<EXTERNAL>' sin biblioteca identificada. "
            "ExternalSpaceAddress es una dirección interna de Ghidra, "
            "no una dirección de ejecución."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "enum": ["old", "new"],
                    "description": "Versión del programa: old para la anterior y new para la nueva.",
                },
            },
            "required": ["version"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
