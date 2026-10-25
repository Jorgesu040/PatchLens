# Ejemplo controlado: tienda-v1 frente a tienda-v2

Caso usado en la ejecución `tienda_intermedia_20261025_104416`, realizada por
Jorge el 25/10/2026. Es un programa propio pequeño para comprobar el pipeline.
No representa una aplicación comercial ni un benchmark general de seguridad.

## Contenido

- `src/tienda-v1.c`, `src/tienda-v2.c`: fuentes de referencia para el evaluador.
- `bin/tienda-v1`, `bin/tienda-v2`: los ELF x86-64 exactos del análisis guardado.
- `execution/raw/`: JSON de los tres motores.
- `execution/normalized.original.json`: JSON de la ejecución con su esquema inicial.
- `execution/normalized.json`: misma evidencia, etiquetada como esquema 2.0 y
  con rutas de informes relativas a la raíz del repositorio para poder revisarlas.
- `execution/agent.json`: historial de llamadas y respuestas del agente.
- `execution/trace.md` y `execution/run.log`: registro y log guardados.
- `execution/report.md`: respuesta final extraída del historial para leerla con
  tablas y Mermaid, sin volver a consultar el modelo.
- `manifest.json`: versiones, hashes, configuración y resumen de la ejecución.
- `SHA256SUMS`: integridad de los archivos de evidencia, fuentes y binarios.
- `build.sh`, `run.sh`: recompilación opcional y comando de nueva ejecución.

No se incluyen credenciales, entornos virtuales ni los proyectos completos de
Ghidra. Una ejecución nueva genera sus propios proyectos bajo `resultados/`.
Las rutas absolutas de los registros pertenecen al entorno de desarrollo;
no son rutas de instalación que deba reproducir quien descargue este ejemplo.

## Cambios conocidos para contrastar el informe

| Función | Cambio de referencia |
|---|---|
| `calcular_subtotal` | Conserva la suma de precios. |
| `calcular_envio` | Umbral de envío gratuito 50 a 75; coste de envío 5. |
| `calcular_descuento` | Nueva: 10 % si cliente_vip es distinto de cero. |
| `mostrar_pedido` | Valida pedido/precios, aplica descuento y muestra desglose. |
| `mensaje_bienvenida` | Se elimina junto a su llamada desde main. |
| `main` | Mantiene el pedido 20 + 15 + 25 y VIP=1; cambian las llamadas. |

Para el pedido fijo, el total deducido es 60 en old y 59 en new. La diferencia
combina 6 de descuento con 5 de envío. Los fuentes no se pasan al agente: este
recibe el JSON normalizado y las consultas de Ghidra.

La copia de fuentes se recuperó del laboratorio del alumno. Sus hashes se
conservan por separado; su nombre por sí solo no prueba identidad con la revisión
histórica compilada. El contraste del informe se ha realizado también con el
pseudocódigo de los binarios exactos, no solo con estos fuentes.

## Revisar el resultado conservado

Desde la raíz de PatchLens:

```bash
(cd example && sha256sum --check SHA256SUMS)
```

Abrir `example/execution/report.md` en un visor Markdown con soporte Mermaid.
Consultar `agent.json` para revisar cada argumento, pseudocódigo y resultado.
La ejecución terminó con `completed`, cuatro rondas de un máximo de veinte y
catorce consultas: dos metadatos, diez funciones, un listado y unas importaciones.

Los JSON originales producen siete propuestas, 23 matches y dos conflictos.
El agente consulta `calcular_envio` old/new y recupera los valores 50 y 75 aunque
la función no aparece en `changes`; relaciona ese cambio con el descuento.
Este hallazgo no equivale a una comparación general de .rodata: no hay lector de
datos del companion set ni garantía de recuperar todos los cambios omitidos.

`matches` se considera parte del esquema 2.0. `normalized.original.json` conserva
la etiqueta del esquema inicial. `normalized.json` utiliza el esquema 2.0 y rutas
de informes relativas al repositorio; ambos contienen los mismos hallazgos.

## Repetir el análisis completo

Instalar primero siguiendo el README raíz, aplicar el parche y autorizar el
modelo. Con `GHIDRA_INSTALL_DIR` configurado y el entorno virtual activo:

```bash
bash example/run.sh gpt-6.1-sol chatgpt
```

Comando equivalente sin el script, desde la raíz:

```bash
python -u Main.py example/bin/tienda-v1 example/bin/tienda-v2 \
  --project-name tienda_nueva_ejecucion \
  --engines VersionTrackingDiff SimpleDiff StructualGraphDiff \
  --provider chatgpt --model gpt-6.1-sol --max-iterations 20
```

El script crea un nombre nuevo y conserva el log. Otra respuesta puede variar,
aunque use el mismo modelo y binarios. No exigir una secuencia idéntica de
consultas: comprobar explicación, evidencia e incertidumbres. La nueva ejecución
no sustituye los resultados conservados en `example/execution/`.

## Recompilar opcionalmente

Comandos recuperados del trabajo original: GCC con C11, `-Wall -Wextra -O0 -g
-fno-inline`. La ejecución conservada usa GCC 13.3.0, con PIE y símbolos de debug.

```bash
bash example/build.sh
```

Genera `resultados/tienda_recompilada/tienda-v1` y `tienda-v2`; mantiene intactos
los binarios históricos de `example/bin/`. Cambiar rutas, compilador u opciones
puede cambiar los bytes y las direcciones por la información de depuración.
No se garantiza reproducir los hashes históricos. Para investigar los nuevos
binarios, pasarlos como entradas a Main con otro nombre de proyecto.
