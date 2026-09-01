# Changelog

## 2.0.0 — 2026-09-01

Grok dashboard in the existing AI meters panel (same icon + popup), published
under a **stable plugin id** that is not a Linux username.

- Plugin id is `shabdar.agents` on every machine. `omarchy plugin add` clones
  into `~/.config/omarchy/plugins/shabdar.agents/` regardless of `$USER`.
  (v1 used `ali.agents`, which was only this machine’s
  `omarchy plugin clone` name.)
- SuperGrok weekly pool % and reset countdown, labeled separately from Bot
- Chat / Imagine / Voice / Build breakdown of that same pool (`—` if unknown)
- Grok Bot weekly % and reset as its own meter (never merged into SuperGrok)
- Credits balance, on-demand on/off and $ this week, status
  (`ok` | `pool exhausted` | `rate-limited`)
- Last job (Chat | Bot | Build) and SuperGrok subscription billing-period end
- Live SuperGrok numbers from Grok Build billing (same pool as grok.com
  Settings → Usage). Grok Bot has no published live API; optional overlay
  `~/.config/omarchy/agents/grok.json` fills Bot and any pinned fields.
- No invented quotas
- Full `Panel.qml` / `Main.qml` ship in the repo so `plugin add` works
  without running `setup.sh` first (`setup.sh` remains for rebasing patches
  after an Omarchy update)

## 1.0.0 — 2026-09-01

First public release.

- Clone of Omarchy's built-in `omarchy.agents` bar widget.
- Adds a Grok / SuperGrok usage collector (`collect-grok.py`) that writes the
  shared weekly pool into `~/.local/state/omarchy/agents/usage/grok.json`.
- Opens the panel on the machine's default coding agent
  (`~/.config/omarchy/defaults/agent`) instead of whichever collector sorts
  first alphabetically (Claude).
- Ships Grok mark SVGs for dark and light surfaces.
