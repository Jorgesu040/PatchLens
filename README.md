# PatchLens

Analizador semántico de cambios entre dos versiones binarias de una aplicación.
Correlaciona diferencias de varios motores de Ghidriff y permite que un único
agente consulte Ghidra para contrastar hipótesis y comprender el efecto conjunto
de la actualización, incluido contexto que no aparece como modificado.

El agente único y sus consultas ya formaban parte del planteamiento inicial.
El avance consiste en su implementación e integración con el pipeline. La
resolución de conflictos entre motores es una posibilidad de la investigación,
no la finalidad exclusiva del programa ni una garantía de su resultado.

## Estado y alcance

- Recorrido desde dos binarios hasta JSON normalizado, investigación y registro
  Markdown. Análisis estático comprobado sobre ELF x86-64 propios escritos en C.
- Tres motores: `VersionTrackingDiff`, `SimpleDiff` y `StructualGraphDiff`
  (nombre original de Ghidriff). Se conservan propuestas y procedencia.
- Diez consultas de lectura sobre ambas versiones: funciones, pseudocódigo,
  llamadas, referencias, cadenas, importaciones y metadatos.
- Registro de solicitudes/resultados, motivo de cierre y límite de iteraciones.
- Caso completo con fuentes, binarios, resultados y comandos en
  [example/](example/README.md).

Las conclusiones requieren revisión. El prototipo no certifica seguridad ni
garantiza detectar todas las diferencias o vulnerabilidades. No ejecuta los
binarios analizados. `companion_set.py` sigue como borrador fuera del flujo.

## Requisitos

Entorno de referencia: Ubuntu/WSL Linux x86-64 y Python 3.12.3. Se ha utilizado
Ghidra **12.0.4**, cuyo mínimo de Java declarado es **21**, y JDK 21.0.12.1.
Ghidra se instala por separado desde sus [releases oficiales](https://github.com/NationalSecurityAgency/ghidra/releases).

Las dependencias Python directas están fijadas en `requirements.txt`: Ghidriff
desde un commit concreto, PyGhidra 3.1.0, JPype1 1.5.2, RapidFuzz 3.14.6,
mdutils 1.6.0 y packaging 26.3. Incluye `requirements-ai.txt`, que fija OpenAI
3.35.1, PyJWT con soporte criptográfico y cryptography. pip resuelve las
dependencias transitivas. `requirements-ai.txt` solo no instala el pipeline completo.

Herramientas de sistema: Git para la dependencia fijada, `patch` para las
correcciones, compilador GCC si se recompila el ejemplo y utilidades de checksum.
Ejemplo para Ubuntu 24.04:

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv openjdk-21-jdk git patch build-essential unzip
```

## Instalación

Desde la raíz del repositorio:

```bash
/usr/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Sustituir por la ruta absoluta de la instalación ya descomprimida.
export GHIDRA_INSTALL_DIR="/ruta/absoluta/ghidra_12.0.4_PUBLIC"
java -version

python patches/ghidriff/apply.py
python patches/ghidriff/apply.py --check
python -m pip check
```

La dependencia original queda fijada al commit
`4f5d895fcbb1eacd65efd81145922c15bb7e741d`. El script aplica las tres correcciones
locales después de comprobar hashes; si ya están aplicadas, solo las verifica.
Detalles y aplicación manual: [patches/ghidriff/README.md](patches/ghidriff/README.md).
No se necesita copiar un entorno virtual ni modificar Ghidra.

JPype incluye componentes nativos. Python 3.12 dispone de la rueda utilizada en
el entorno probado; cambiar de versión de Python puede requerir compilación y
no se considera una instalación equivalente comprobada.

## Credenciales y elección de modelo

Para la modalidad implementada con sesión de ChatGPT:

```bash
python AI.py login
# En WSL, si no se abre el navegador:
python AI.py login --no-browser
```

Completar la autorización interactiva. La disponibilidad del modelo y acceso
dependen de la cuenta. La sesión queda local en `.patchlens-auth/`, ignorado por
Git; no se incluye en el ejemplo ni debe compartirse.

Alternativamente, definir `OPENAI_API_KEY` en el entorno y ejecutar con
`--provider api-key`. No escribir la clave en scripts ni en el README.

## Ejecución completa

```bash
python -u Main.py example/bin/tienda-v1 example/bin/tienda-v2 \
  --project-name mi_comparacion \
  --engines VersionTrackingDiff SimpleDiff StructualGraphDiff \
  --provider chatgpt --model gpt-6.1-sol --max-iterations 20
```

El modelo es el indicado en el comando de reproducción; sustituirlo si la cuenta
ofrece otro. El historial original no conserva el identificador del modelo como
metadato de ejecución; esta limitación figura en el manifiesto del ejemplo.
Para generar un nombre de ejecución nuevo y conservar el log:

```bash
bash example/run.sh gpt-6.1-sol chatgpt
```

Los motores se ejecutan secuencialmente. `--timeout 1800` limita cada proceso;
`--max-iterations` limita las rondas del agente, no el número total de consultas.
Las herramientas abren los dos programas del proyecto del primer motor solicitado.
Con el orden predeterminado se utiliza el proyecto de VersionTrackingDiff como
base de consulta, manteniendo las propuestas de los tres motores en el JSON.

Salidas bajo `resultados/`:

- `<nombre>/`: originales y proyectos generados por cada motor, en directorios nuevos.
- `<nombre>.json`: JSON conjunto del esquema 2.0.
- `<nombre>.md.agent.json`: historial de la investigación y motivo de terminación.
- `<nombre>.md`: registro Markdown, incluida la respuesta final del agente.

Usar nombres distintos para conservar ejecuciones: los archivos con el mismo
nombre de proyecto se reemplazan. Un fallo de motor detiene el pipeline; el
registro del agente señala una parada por límite/error como resultado parcial.

Sin `--model`, Main realiza solo comparación y normalización, sin inferencia.
`AI.py analyze` por separado procesa un JSON sin abrir Ghidra ni suministrar las
consultas: para el recorrido con herramientas utilizar `Main.py --model`.

## JSON normalizado: esquema 2.0

`matches` forma parte del esquema **2.0**, junto a:

| Campo | Contenido |
|---|---|
| `binaries` | Identidad, SHA256 y metadatos de old/new. |
| `analyses` | Informe original y estadísticas de cada motor. |
| `changes` | Propuestas añadidas/eliminadas/modificadas, funciones, aspectos, fuentes e IDs. |
| `matches` | Correspondencias old/new propuestas, métodos, fuentes y `match_id`; también fuera de changes. |
| `conflicts` | Clasificaciones/correspondencias incompatibles, enlazadas por change_ids y match_ids. |

`sources.analysis` identifica el motor; `sources.json_path`, su registro original.
Una coincidencia de varios motores no es una votación de verdad. Una función
ausente de `changes` puede haber cambiado; una correspondencia no demuestra
equivalencia. Las funciones conservan `called` y `calling` de Ghidriff.

El parser comprueba hashes de ambas versiones antes de fusionar y conserva las
propuestas incompatibles. Si distintas fuentes de una misma propuesta exportan
datos incompatibles, se detiene con `ValueError`. Los IDs dependen del orden de
entrada. `schema_version` es una etiqueta, no un validador de todos los campos.

## Revisar el ejemplo sin Ghidra ni nuevas llamadas al modelo

Abrir [el informe final guardado](example/execution/report.md) y consultar su
traza, binarios y fuentes según [example/README.md](example/README.md).
Para regenerar únicamente la normalización de los JSON originales:

```bash
python GhidriffParser.py \
  --report VersionTrackingDiff=example/execution/raw/VersionTrackingDiff.json \
  --report SimpleDiff=example/execution/raw/SimpleDiff.json \
  --report StructualGraphDiff=example/execution/raw/StructualGraphDiff.json \
  --output resultados/tienda-replay.json
```

Las fuentes C son referencia de evaluación, no entrada del agente. Las
direcciones de funciones pueden cambiar al recompilar con otro compilador u opciones.

## Pruebas y organización

```bash
python -B -m unittest discover -s tests -v
```

La instalación desde requirements.txt, aplicación del parche, comparación de los
tres motores y consultas old/new se han comprobado en un entorno virtual limpio;
pip check no detecta incompatibilidades. La suite del proyecto tiene 50 pruebas. Las pruebas de IA usan respuestas simuladas y no miden calidad
semántica. La ejecución conservada usa tres motores, siete propuestas, 23 matches
y dos conflictos; el agente termina en cuatro rondas y hace 14 consultas sin error.
No equivale a una evaluación sobre aplicaciones reales variadas.

Componentes principales: `Main.py` orquesta; `GhidriffParser.py` adapta;
`parser/NormalizerEngine.py` correlaciona; `AIAdapters.py` ejecuta el bucle;
`AI.py` define instrucciones y registro; `model_tools/` consulta ambos programas.
Ghidra/Ghidriff realizan descompilación y matching.

## Próximos pasos

- Implementar las consultas pendientes de `companion_set.py`.
- Definir el informe con una visión general y el detalle de cada cambio.
- Permitir preguntas posteriores al mismo agente y desarrollar la interfaz gráfica.
- Evaluar casos variados y un parche público de seguridad.
- Investigar la incorporación de análisis dinámico. El ranking de cambios es opcional.
