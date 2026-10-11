#!/bin/bash
set -e
exec python3 -B "$(cd "$(dirname "$0")" && pwd)/validate.py" "$@"
