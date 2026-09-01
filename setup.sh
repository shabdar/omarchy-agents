#!/bin/bash
# Rebuild Panel.qml / Main.qml / Agent.qml from Omarchy's stock agents plugin
# plus the patches in ./patches. Safe to re-run.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
stock="${OMARCHY_PATH:-/usr/share/omarchy}/shell/plugins/agents"
for f in Main.qml Panel.qml Agent.qml; do
  [[ -f $stock/$f ]] || { echo "setup.sh: missing $stock/$f" >&2; exit 1; }
  cp "$stock/$f" "$here/$f"
  patch -s -p1 -d "$here" < "$here/patches/$f.diff"
done
chmod +x "$here/collect-grok.py" "$here/refresh-usage.sh" "$here/setup.sh"
echo "Applied Grok/default-agent patches to $here"
echo "Plugin id is shabdar.agents (publisher id). Enable with:"
echo "  omarchy plugin enable shabdar.agents --section right --yes"
