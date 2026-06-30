#!/usr/bin/env bash
# Launch MindMapo
cd "$(dirname "$0")" || exit 1
exec python3 main.py "$@"
