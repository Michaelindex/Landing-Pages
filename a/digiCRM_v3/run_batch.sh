#!/usr/bin/env bash
set -euo pipefail
BATCH=${1:-5000}
WORKERS=${WORKERS:-500}
source .venv/bin/activate
python -m src.orchestrator --batch "$BATCH" --workers "$WORKERS"
