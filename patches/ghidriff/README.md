# Parches locales de Ghidriff

Origen: [clearbluejar/ghidriff](https://github.com/clearbluejar/ghidriff), commit
`4f5d895fcbb1eacd65efd81145922c15bb7e741d`, que declara versión `1.0.0`.
`requirements.txt` fija ese commit. El parche no se presenta como una versión
publicada por el proyecto original. Se conserva su licencia en `LICENSE.upstream`.

## Correcciones incluidas

1. `simple_diff.py` y `structural_graph_diff.py`: exportar métodos de matching
   como listas para que el motor común no cuente caracteres como métodos.
2. `ghidra_diff_engine.py`: actualizar la caché cuando se solicita pseudocódigo
   tras recuperar metadatos; conservar la información completa y proteger las
   consultas concurrentes del mismo símbolo con un lock.
3. `structural_graph_diff.py`: retirar el segundo llenado de candidatas que
   producía funciones añadidas/eliminadas repetidas en el caso tienda.

El diagnóstico y las modificaciones se prepararon con asistencia de Codex y se
comprobaron con pruebas de regresión y salidas reales. No son un nuevo motor de
comparación y no garantizan recuperar todos los cambios de cualquier binario.

## Aplicación recomendada

Desde la raíz de PatchLens, con el entorno virtual de instalación activado:

```bash
python -m pip install -r requirements.txt
python patches/ghidriff/apply.py
python patches/ghidriff/apply.py --check
```

El script localiza Ghidriff en ese intérprete y comprueba los SHA256 de los tres
archivos. Si ya está aplicado, no lo repite. Si hay una versión diferente o un
estado mixto, se detiene. Los hashes originales y modificados están en `apply.py`.
Una reinstalación de Ghidriff puede retirar el parche: ejecutar de nuevo `--check`.

## Aplicación manual equivalente

```bash
ghidriff_site=$(python -c 'import importlib.util; from pathlib import Path; print(Path(importlib.util.find_spec("ghidriff").origin).resolve().parent.parent)')
patch --dry-run -p1 -d "$ghidriff_site" < patches/ghidriff/ghidriff-local.patch
patch -p1 -d "$ghidriff_site" < patches/ghidriff/ghidriff-local.patch
python patches/ghidriff/apply.py --check
```

La vía manual solo debe utilizarse sobre los archivos base indicados. Para
revertir, usar `patch --reverse`, primero con `--dry-run`, sobre la misma copia.

## Evidencia y límites

Las salidas conservadas en `example/execution/raw/` permiten revisar los
métodos, el pseudocódigo y la ausencia de duplicados en el caso tienda.
La aplicación del parche se comprueba con `python patches/ghidriff/apply.py --check`.
