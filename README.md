# ali.agents — Omarchy AI usage meters (v1.0.0)

An [Omarchy](https://omarchy.org/) status-bar plugin that shows rate-limit
**meters** for the AI coding agents on the machine. Clicking the AI icon
opens **your default agent first** (Grok, if that is what you chose), not
Claude.

This is a clone of Omarchy's built-in `omarchy.agents` widget, plus:

1. A **Grok / SuperGrok collector** (stock Omarchy only ships Claude, Codex,
   and Fireworks).
2. Panel selection that follows `omarchy default agent` instead of
   alphabetical order.

**Version:** 1.0.0
**Plugin id:** `ali.agents`
**License:** MIT (see [LICENSE](LICENSE))

---

## Where this lives on the machine

The running copy is the Omarchy user plugin directory:

```
~/.config/omarchy/plugins/ali.agents/
```

Omarchy cloned the built-in widget here (`omarchy plugin clone omarchy.agents`)
and switched the bar slot from `omarchy.agents` to `ali.agents`. Saved edits
hot-reload.

Usage records the panel *displays* are **not** in this folder. Collectors
write them to:

```
~/.local/state/omarchy/agents/usage/
  grok.json
  claude.json
  codex.json
  fireworks.json
```

---

## Why it exists

Omarchy's stock AI button (`omarchy.agents`) only knows Claude, Codex, and
Fireworks. It also opens on the first enabled provider in alphabetical order,
so a machine whose default agent is Grok still lands on Claude's meters.

This plugin:

- Collects SuperGrok's shared weekly usage pool (the same percentage as
  grok.com → Settings → Usage).
- Sorts and selects the provider named in `~/.config/omarchy/defaults/agent`.

---

## Requirements

- [Omarchy](https://omarchy.org/) with `omarchy-shell`
- `python3` and `jq` (both present on a stock Omarchy install)
- For Grok meters: Grok Build signed in (`grok login`), which writes
  `~/.grok/auth.json`

Claude / Codex / Fireworks meters still use Omarchy's packaged collectors
(`omarchy-agent-usage-claude`, `-codex`, `-fireworks`).

---

## Install

### Already running on this machine

Nothing else to install. The bar widget id is `ali.agents`. Confirm with:

```bash
omarchy plugin list | grep agents
# ali.agents should be enabled; omarchy.agents disabled
```

### From GitHub (another Omarchy machine)

```bash
omarchy plugin add https://github.com/shabdar/omarchy-agents.git --enable --yes
```

That clones into `~/.config/omarchy/plugins/ali.agents/` (the manifest `id`).
If a clone of `omarchy.agents` is already in that path, remove or rename it
first, or pull this repo into the existing folder.

Then make sure the bar is using it:

```bash
# shell.json bar.layout.right should contain { "id": "ali.agents" }
# not { "id": "omarchy.agents" }
```

Sign in to Grok, then refresh:

```bash
grok login
~/.config/omarchy/plugins/ali.agents/refresh-usage.sh --force
omarchy-shell shell rescanPlugins
```

### Update

If this directory is a git checkout of the GitHub repo:

```bash
omarchy plugin update ali.agents
```

---

## Using the panel

| Input | Action |
| --- | --- |
| Left-click the AI icon | Open / close the meters panel |
| Right-click | Launch an agent (`omarchy-agent --pick`) |
| Middle-click | Next subscription |
| `h` / `l` | Previous / next subscription |
| `j` / `k` | Scroll |
| `r` or Enter | Refresh |
| Esc | Close |

IPC (the clone keeps the stock target so existing bindings still work):

```bash
omarchy-shell omarchy.agents toggle
omarchy-shell omarchy.agents refresh
omarchy-shell omarchy.agents next
```

---

## What you should see

On a machine whose default agent is Grok and that is signed in:

1. Click the AI icon in the top bar.
2. The hero reads **Grok** / **SuperGrok**.
3. **LIMITS** shows a **Weekly** meter (percent of the SuperGrok pool used)
   and a reset countdown.
4. If Claude (or another agent) also has usage, a switcher row appears so
   you can flip to it.

The Grok tab does not yet chart tokens-by-day or tokens-by-model. Grok
session files do not expose billed token totals the way Claude transcripts
do; the weekly pool is the authoritative SuperGrok meter.

---

## How it works

```
Bar click
  → Panel.qml
      → selects ~/.config/omarchy/defaults/agent  (e.g. grok)
      → Main.qml lists ~/.local/state/omarchy/agents/usage/*.json
      → refresh timer runs refresh-usage.sh
           → omarchy-agent-usage-update   (claude / codex / fireworks)
           → collect-grok.py              (stdout JSON → grok.json)
```

`collect-grok.py` reads the Grok Build OIDC token from `~/.grok/auth.json`,
calls `cli-chat-proxy.grok.com/v1/billing?format=credits`, and maps
`creditUsagePercent` onto the panel's `limits[]` contract (`percent` is 0..1).
Plan name comes from `/v1/settings` (`subscription_tier_display`).

Tokens are used in memory only. An expired access token is refreshed against
`https://auth.x.ai/oauth2/token`; the new token is **not** written back to
`auth.json` (Grok CLI owns that file). If refresh fails, run `grok login`.

A 15-second cache at `~/.cache/omarchy/agent-usage/grok-limits.json` stops
the panel from probing on every open. `--force` skips it.

---

## File map

| Path | Role |
| --- | --- |
| `manifest.json` | Omarchy plugin id `ali.agents`, version `1.0.0` |
| `Panel.qml` | Bar button + popup; prefers the default agent |
| `Main.qml` | Discovers usage JSON, runs `refresh-usage.sh`, sorts default agent first |
| `Agent.qml` | Watches one usage JSON file |
| `refresh-usage.sh` | Packaged collectors + Grok collector |
| `collect-grok.py` | SuperGrok weekly-pool probe (prints JSON) |
| `assets/grok.svg` | Grok mark for dark surfaces |
| `assets/grok-light.svg` | Grok mark for light surfaces |
| `assets/claude.svg`, `codex.svg`, `codex-light.svg`, `fireworks.svg` | Stock marks from Omarchy |

---

## Settings

Widget settings live on the `ali.agents` entry in `~/.config/omarchy/shell.json`.

```bash
omarchy bar set ali.agents refreshIntervalSec 300 --json
omarchy bar set ali.agents providers '{
  "grok": { "enabled": true },
  "claude": { "enabled": true },
  "codex": { "enabled": false },
  "fireworks": { "enabled": false }
}' --json
```

| Key | Default | Meaning |
| --- | --- |
| `refreshIntervalSec` | `900` | How often usage records regenerate |
| `providers.<id>.enabled` | `true` | Hide a subscription |
| `syncMode` | `"Off"` | Merge usage snapshots from other machines |
| `syncDir` | `""` | Folder synced by Syncthing / Dropbox / rsync |

Default agent (what the panel opens on):

```bash
omarchy default agent          # print
omarchy default agent grok     # set
# stored in ~/.config/omarchy/defaults/agent
```

---

## Troubleshooting

**Panel still opens on Claude**
Check `cat ~/.config/omarchy/defaults/agent` is `grok`, that
`~/.local/state/omarchy/agents/usage/grok.json` exists and has a `limits`
array, and that the bar widget id is `ali.agents`.

**No Grok tab**
The panel hides agents with nothing to show. Run
`python3 ~/.config/omarchy/plugins/ali.agents/collect-grok.py` and confirm
JSON with `"id":"grok"` and a non-empty `limits` list. Sign in with
`grok login` if status is "Waiting for auth" or "Sign-in expired".

**Collector failed**
`refresh-usage.sh` leaves the previous `grok.json` in place. Look at
`omarchy-shell` logs, or run the collector in a terminal (it never prints
tokens).

**Stock `omarchy.agents` came back after an Omarchy update**
Re-enable this clone: the bar layout should reference `ali.agents`.

---

## Versioning

GitHub release **v1.0.0** matches `manifest.json` `"version": "1.0.0"`.
See [CHANGELOG.md](CHANGELOG.md).

---

## Credits

- Original `omarchy.agents` widget: [Omarchy](https://github.com/basecamp/omarchy) (MIT)
- Grok collector, default-agent selection, and this packaging: Ali Shabdar
