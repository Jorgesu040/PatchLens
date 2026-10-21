# Fixtures de Ghidriff parcheado

Copias sin modificar de los tres originales enlazados en
`resultados/tienda_ghidriff_dedup.json`. Las carpetas de aquella ejecución son:

- `VersionTrackingDiff-akqixv43`.
- `SimpleDiff-p59a21h5`.
- `StructualGraphDiff-kinatm74`.

Cada carpeta está bajo `resultados/tienda_ghidriff_dedup/` y contiene
`json/tienda-v1-tienda-v2.ghidriff.json`. Las identidades de los binarios están
en old_meta/new_meta de cada fixture. Este es el único conjunto de fixtures
de tienda; las copias anteriores defectuosas se retiraron de tests/fixtures.
Sus informes de ejecución siguen disponibles en resultados/.

Este conjunto contiene métodos como listas, pseudocódigo en añadidas/eliminadas
y ninguna duplicación de candidatas de Structural. Genera 14 fuentes que se
agrupan en 7 propuestas y 1 conflicto, enlazado por IDs en el resultado final.
