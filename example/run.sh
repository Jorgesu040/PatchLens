#!/usr/bin/env bash
set -euo pipefail

patchlens_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$patchlens_root"
patchlens_model=${1:-gpt-6.1-sol}
patchlens_provider=${2:-chatgpt}
patchlens_run="tienda_$(date +%Y%m%d_%H%M%S)_$$"
mkdir -p resultados

python -u Main.py example/bin/tienda-v1 example/bin/tienda-v2 \
  --project-name "$patchlens_run" \
  --engines VersionTrackingDiff SimpleDiff StructualGraphDiff \
  --provider "$patchlens_provider" --model "$patchlens_model" --max-iterations 20 \
  2>&1 | tee "resultados/${patchlens_run}.log"
