#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="$PROJECT_ROOT/data"

MAC_HOST="${YAHOO_MAC_HOST:-}"
MAC_USER="${YAHOO_MAC_USER:-}"
MAC_DIR="${YAHOO_MAC_DIR:-}"

if [[ -z "$MAC_HOST" || -z "$MAC_USER" || -z "$MAC_DIR" ]]; then
    cat <<'EOF'
Missing MacBook connection settings.

Set these variables on the Pi, for example in ~/.profile:

  export YAHOO_MAC_HOST="your-macbook.local"
  export YAHOO_MAC_USER="your-mac-username"
  export YAHOO_MAC_DIR="~/Downloads"

Then reload your shell:

  source ~/.profile
EOF
    exit 2
fi

mkdir -p "$DEST_DIR"

echo "Pulling Yahoo files from $MAC_USER@$MAC_HOST:$MAC_DIR"
echo "Destination: $DEST_DIR"
echo

rsync     -av     --progress     --prune-empty-dirs     --include='Yahoo_*'     --exclude='*'     "$MAC_USER@$MAC_HOST:$MAC_DIR/"     "$DEST_DIR/"

echo
echo "Yahoo data pull complete."
echo "Run the Weekly page refresh, or:"
echo "  python -m tools.html_fallback_import"
