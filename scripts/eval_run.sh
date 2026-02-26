#!/bin/bash
set -euo pipefail

uv run python scripts/eval_run.py "$@"
