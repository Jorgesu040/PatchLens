#!/usr/bin/env bash
set -euo pipefail

patchlens_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$patchlens_root"
mkdir -p resultados/tienda_recompilada
gcc -std=c11 -Wall -Wextra -O0 -g -fno-inline example/src/tienda-v1.c -o resultados/tienda_recompilada/tienda-v1
gcc -std=c11 -Wall -Wextra -O0 -g -fno-inline example/src/tienda-v2.c -o resultados/tienda_recompilada/tienda-v2
sha256sum resultados/tienda_recompilada/tienda-v1 resultados/tienda_recompilada/tienda-v2
