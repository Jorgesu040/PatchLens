# Consultas a Ghidra desde PatchLens

`GhidraSession` abre un proyecto existente y mantiene dos `Program` disponibles:
`old` es la versión antigua y `new` la nueva. No ejecuta el análisis de nuevo.
Es un singleton por proceso: las consultas de `main_set` usan el mismo `session`.
Importar el paquete no arranca Java; `session.open(...)` abre la sesión.

Para el caso tienda usamos el proyecto de **VersionTrackingDiff** de la ejecución
`tienda_ghidriff_dedup`. Esta elección fija la base de consulta, no valida sus
emparejamientos ni descarta los resultados o conflictos de las otras engines.
No se mezclan objetos Program de proyectos distintos. Si se cambia de ejecución,
hay que seleccionar su .gpr y las rutas internas de sus programas.

## Comprobar la conexión en WSL

Desde `/home/jorge/PatchLens/PatchLens-repo`:

```bash
../.venv-ghidriff/bin/python -m model_tools.main_set \
  --ghidra-install /home/jorge/PatchLens/ghidra_12.0.4_PUBLIC \
  --project resultados/tienda_ghidriff_dedup/VersionTrackingDiff-akqixv43/ghidra_projects/tienda_ghidriff_dedup-tienda-v1-tienda-v2/tienda_ghidriff_dedup-tienda-v1-tienda-v2.gpr \
  --program-old /tienda-v1-6964e9 \
  --program-new /tienda-v2-77f03a
```

Ghidriff añade sufijos a los nombres internos. No basta con `/tienda-v1`.
Si se omite `--ghidra-install`, PyGhidra usa su configuración de instalación,
incluida la variable `GHIDRA_INSTALL_DIR`. Si la JVM ya está iniciada, se reutiliza.

## Usarlo desde las herramientas

```python
from model_tools import session

session.open(project_file, program_old, program_new, install_dir)
try:
    # Program nativos de Ghidra:
    functions_old = session.old.getFunctionManager()
    memory_new = session.new.getMemory()

    # FlatProgramAPI de cada versión:
    address = session.flat_old.toAddr("001011f9")
    function = functions_old.getFunctionContaining(address)

    # Selección mediante el argumento version que envíe el agente:
    program = session["old"]  # Solo "old" o "new".
    listing = program.getListing()

    # Ejecutar aquí el bucle del agente y sus consultas.
finally:
    session.close()
```

`main_set` importa `session` desde `.ghidra_session`; sus funciones pueden
usar directamente `session[version]`, `session.flat_old` o `session.flat_new`.
`GhidraSession()` devuelve ese mismo objeto y no reinicia sus campos.
Solo el punto de entrada debe llamar a `open`: una segunda apertura sin cerrar
produce un error para no cambiar los binarios que las herramientas consultan.

No se usa ExitStack. `consume_program` obtiene cada Program y su consumer;
`close` llama a `release(consumer)` en `new` y `old` y cierra el proyecto. Si falla
la apertura de `new`, se libera `old` y se cierra el proyecto. Se puede repetir `close`
y, después, abrir otra comparación.

También se registra `close` con `atexit`, después del arranque de la JVM, para
limpiar al finalizar normalmente el proceso. No cubre una terminación forzada.
El try/finally del ejemplo cierra justo al terminar la investigación. No guardar
referencias a objetos Java después del cierre. No se guardan modificaciones ni
se detiene la JVM. El singleton está pensado para el bucle secuencial: no ofrece
sincronización entre hilos ni comparte memoria con otros procesos. Si el proyecto
está abierto en otra aplicación, puede ser necesario cerrarlo allí.

Las diez consultas de `main_set.py` están implementadas, descritas en
`schema_tools/main_set_schemas.py` y conectadas desde `Main.py --model`.
`companion_set.py` es un borrador pendiente y no se importa en el flujo de esta
entrega. Sus funciones previstas son get_disassembly, read_data, list_segments
y list_data_items; el comienzo de get_disassembly todavía no devuelve un resultado.

La instalación y ejecución portátil se describen en el README de la raíz.
La ruta de tienda_ghidriff_dedup de esta guía es una referencia histórica local;
Main abre el proyecto generado en cada ejecución y sus nombres internos.

## Orientación para elegir API · 2026-10-24

El manager actual ya expone `session.flat_old` y `session.flat_new`. Para una
herramienta que recibe `version`, elige una de esas referencias. Pista: observa
cómo `__getitem__` selecciona el Program. No existe todavía un selector de
FlatAPI equivalente; no necesitas crear otra instancia por consulta.

La guía del Brain `02-Asignaturas/prcc/recursos/2026-10-21-ghidra-python-patchlens.md`
incluye una actualización al principio con las doce herramientas, métodos,
referencias y preguntas para implementarlas. Conserva los ejemplos anteriores
como ejercicios históricos, no como el ciclo de apertura actual de PatchLens.

Para lo que llevas: `get_binary_info` encaja con Program; `list_functions` encaja
con el iterador del FunctionManager; la localización en `get_function` se puede
acortar con `toAddr` y `getFunctionAt` de FlatProgramAPI. El descompilador es otra
API: puedes conservar DecompInterface o estudiar FlatDecompilerAPI.

Referencias: [FlatProgramAPI](https://ghidra.re/ghidra_docs/api/ghidra/program/flatapi/FlatProgramAPI.html)
y [FlatDecompilerAPI](https://ghidra.re/ghidra_docs/api/ghidra/app/decompiler/flatapi/FlatDecompilerAPI.html).
