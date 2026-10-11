#!/usr/bin/env bash
# macOS and Linux (including WSL 2). Run from a persistent Git checkout.
set -euo pipefail
command -v python3 >/dev/null 2>&1 || {
    echo 'Python 3.9+ is required. Install Python with your package manager, then rerun ./install.sh.' >&2
    exit 1
}
exec python3 "$(cd "$(dirname "$0")" && pwd)/scripts/setup.py" "$@"
