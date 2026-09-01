#!/bin/bash
# refresh-usage.sh — regenerate every agents-panel usage record this widget shows.
#
# Stock Omarchy only runs collectors that live in $OMARCHY_PATH/bin
# (claude, codex, fireworks). This wrapper:
#   1. runs `omarchy-agent-usage-update` for those packaged collectors
#   2. runs `collect-grok.py` and atomically writes grok.json
#
# Main.qml invokes this script on the widget refresh timer and on manual
# refresh. Flags are forwarded unchanged:
#   --force          rescan / re-probe
#   --limits-only    cheaper refresh used when the panel opens
#   --except <id>    skip a provider
#   <agent...>       only those agents
#
# Exit status is non-zero if either step fails. A failed Grok probe does not
# delete an existing grok.json.

set -u

here=$(cd "$(dirname "$0")" && pwd)
status=0
omarchy-agent-usage-update "$@" || status=1

run_grok=1
only=()
args=("$@")
i=0
while (( i < ${#args[@]} )); do
  case "${args[$i]}" in
  --except)
    i=$((i + 1))
    if [[ ${args[$i]:-} == grok ]]; then
      run_grok=0
    fi
    ;;
  --force | --limits-only) ;;
  *) only+=("${args[$i]}") ;;
  esac
  i=$((i + 1))
done

if (( ${#only[@]} > 0 )); then
  run_grok=0
  for agent in "${only[@]}"; do
    [[ $agent == grok ]] && run_grok=1
  done
fi

if (( run_grok )); then
  usage_dir="${XDG_STATE_HOME:-$HOME/.local/state}/omarchy/agents/usage"
  mkdir -p "$usage_dir"
  if record=$("$here/collect-grok.py" "$@") && [[ -n $record ]] && jq -e . >/dev/null 2>&1 <<<"$record"; then
    tmp=$(mktemp "$usage_dir/.grok.XXXXXX")
    printf '%s\n' "$record" >"$tmp"
    chmod 600 "$tmp"
    mv "$tmp" "$usage_dir/grok.json"
  else
    echo "ali.agents: grok collector failed" >&2
    status=1
  fi
fi

exit "$status"
