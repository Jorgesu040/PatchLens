# PatchLens
AI-assisted investigation of binary changes using Ghidra and Ghidriff.

## Estado del prototipo

Compara un par de binarios con `VersionTrackingDiff`, `SimpleDiff` y
`StructualGraphDiff` (este último nombre conserva la grafía de Ghidriff).
Normaliza las propuestas, conserva las fuentes y señala clasificaciones o
correspondencias incompatibles. No decide automáticamente cuál es correcta.
El análisis de IA actual recibe el contexto en una llamada; todavía no dispone
de herramientas para consultar Ghidra durante la investigación.

## Ejecutar en el entorno WSL del proyecto

Requiere Python, Ghidra con su JDK compatible y Ghidriff instalado. En el entorno
actual, Ghidriff está en `../.venv-ghidriff/bin/ghidriff`; el runner también busca
en PATH y junto al intérprete Python activo.

```bash
cd /home/jorge/PatchLens/PatchLens-repo
export GHIDRA_INSTALL_DIR=/home/jorge/PatchLens/ghidra_12.0.4_PUBLIC
.venv-ai/bin/python Main.py ruta/binario-v1 ruta/binario-v2 --project-name mi_comparacion
```

`--engines SimpleDiff` permite ejecutar solo ese motor; `--timeout 300` establece
el límite en segundos para cada proceso. Los motores se ejecutan secuencialmente.
Cada ejecución guarda originales en una carpeta nueva bajo
`resultados/mi_comparacion/`; el resultado normalizado se escribe en
`resultados/mi_comparacion.json` (se reemplaza si ya existe).
Un fallo de un motor detiene la ejecución: no se presenta una comparación
completa con resultados antiguos de ese motor.

## Normalizar informes existentes sin volver a ejecutar Ghidra

```bash
python GridriffParser.py \
  --report VersionTrackingDiff=tests/fixtures/tienda/VersionTrackingDiff.json \
  --report SimpleDiff=tests/fixtures/tienda/SimpleDiff.json \
  --report StructualGraphDiff=tests/fixtures/tienda/StructualGraphDiff.json \
  --output resultados/tienda-replay.json
```

Los informes deben pertenecer al mismo par de binarios. Se comparan los SHA256
old/new antes de agruparlos. Se asume el formato de salida válido de Ghidriff:
si falta un campo necesario, el parser se detiene, sin producir resultados parciales.
El normalizador espera `match_types` como lista de la instalación parcheada.

## JSON normalizado: esquema 2.0

- `binaries`: identidad y metadatos de las versiones antigua y nueva.
- `analyses`: ruta del informe original y estadísticas de cada motor.
- `changes`: propuestas agrupadas por tipo y direcciones old/new. Incluyen
  `aspects`, funciones, `sources`, `change_id` y `conflict_ids`.
- `conflicts`: discrepancias de clasificación o correspondencia; enlazan las
  propuestas afectadas mediante `change_ids`; los índices solo se usan internamente.

Las funciones conservan `called` (funciones a las que llaman) y `calling`
(funciones que las llaman), con los nombres originales de Ghidriff. No se crean
alias `callees`/`callers`.

`sources` conserva motor, ruta dentro del JSON original y aspectos detectados.
Dos rutas distintas del mismo motor se conservan; no representan dos motores
independientes. Para agrupar dos registros de la misma propuesta deben coincidir
las exportaciones de cada lado; si difieren, se lanza `ValueError`, sin variantes
ni selección silenciosa. Esto no exige que old y new sean iguales: el cambio
entre versiones se conserva. No se selecciona por mayoría ni por longitud del pseudocódigo.
Los IDs dependen del orden de entrada, no son hashes globales estables.

En el caso tienda, los originales contienen 16 registros que se agrupan en 7
propuestas y una alerta `added_vs_modified` para `calcular_descuento`. La ausencia
de `calcular_envio` en estos diffs sigue siendo una limitación: unir informes no
recupera por sí solo información que ninguno exportó.

La instalación local tiene tres parches documentados en
`experiments/2026-10-21-ghidriff-local-patches/README.md`: métodos como listas,
caché de descompilación y duplicados de Structural. Con ellos, la ejecución
`resultados/tienda_ghidriff_dedup.json` conserva las mismas 7 propuestas y 1
conflicto, con 14 fuentes sin las dos entradas repetidas de Structural.
`tests/fixtures/tienda/` contiene únicamente las salidas corregidas; los informes
históricos de ejecución se conservan en `resultados/`.

## Componentes

- `Main.py`: ejecución de motores y localización del informe esperado.
- `GridriffParser.py`: único parser, lectura, selección de campos y fusión.
- `parser/NormalizerEngine.py`: identidad, unión, detección y enlaces de conflictos.
- `AI.py`: envía el informe actual al modelo, sin comprobar versión ni estructura.

Las funciones existentes se adaptan al formato nuevo: `_copy_function` selecciona
campos, `get_functions` normaliza un grupo, `get_changes` reúne los tres grupos,
y `parse_json` lee un informe. `parse_reports` comprueba hashes, fusiona y enlaza
conflictos. La aplicación asume el formato actual; `schema_version` es solo
una etiqueta informativa y no activa validaciones ni rutas alternativas.
El archivo de ejercicios en `experiments/` no es el módulo de producción.

## Verificación sin llamadas de IA

```bash
.venv-ai/bin/python -B -m unittest discover -s tests -v
```

Las pruebas de IA usan adaptadores simulados: no acreditan la calidad de una
respuesta de un modelo real. Los archivos de tienda son salidas reales del
experimento controlado, no un benchmark de superioridad entre motores.
