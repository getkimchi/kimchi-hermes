#!/usr/bin/env bash
# Install the Kimchi provider plugins into Hermes' user-plugin directory.
# Uninstall: rm -rf ~/.hermes/plugins/model-providers/kimchi{,-acp}
set -euo pipefail

DEST="${HERMES_HOME:-$HOME/.hermes}/plugins/model-providers"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/model-providers"

if [[ ! -d "$SRC/kimchi" || ! -d "$SRC/kimchi-acp" ]]; then
	echo "error: model-providers/{kimchi,kimchi-acp} not found next to install.sh" >&2
	exit 1
fi

mkdir -p "$DEST"
rm -rf "$DEST/kimchi" "$DEST/kimchi-acp"
cp -R "$SRC/kimchi" "$SRC/kimchi-acp" "$DEST/"

echo "Installed Kimchi provider plugins to $DEST"
echo "Next: run 'hermes model' and pick 'Kimchi' or 'Kimchi (Harness via ACP)'."
