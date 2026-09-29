#!/usr/bin/env bash
# Install the Kimchi provider plugins into Hermes' user-plugin directory
# (and every profile home, for profile-scoped Desktop bots/gateways).
# Uninstall: rm -rf ~/.hermes/plugins/model-providers/kimchi{,-acp}
#            rm -rf ~/.hermes/profiles/*/plugins/model-providers/kimchi{,-acp}
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/model-providers"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

if [[ ! -d "$SRC/kimchi" || ! -d "$SRC/kimchi-acp" ]]; then
	echo "error: model-providers/{kimchi,kimchi-acp} not found next to install.sh" >&2
	exit 1
fi

targets=("$HERMES_HOME/plugins/model-providers")
# Profile-scoped homes (Desktop bots run their own gateways with their own
# plugin dirs — main-home installs are invisible to them).
for profile_dir in "$HERMES_HOME"/profiles/*/; do
	[[ -d "$profile_dir" ]] && targets+=("${profile_dir}plugins/model-providers")
done

for dest in "${targets[@]}"; do
	mkdir -p "$dest"
	rm -rf "$dest/kimchi" "$dest/kimchi-acp"
	cp -R "$SRC/kimchi" "$SRC/kimchi-acp" "$dest/"
	echo "Installed -> $dest"
done

echo "Next: run 'hermes model' and pick 'Kimchi' or 'Kimchi (Harness via ACP)'."
echo "Desktop note: GUI-launched apps have a minimal PATH — if the Desktop app"
echo "fails to find the kimchi CLI, set it for GUI processes:"
echo "  launchctl setenv KIMCHI_ACP_COMMAND \"\$HOME/.local/bin/kimchi\""
echo "then fully restart the Hermes Desktop app."
