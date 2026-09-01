# Changelog

## 1.0.0 — 2026-09-01

First public release.

- Clone of Omarchy's built-in `omarchy.agents` bar widget.
- Adds a Grok / SuperGrok usage collector (`collect-grok.py`) that writes the
  shared weekly pool into `~/.local/state/omarchy/agents/usage/grok.json`.
- Opens the panel on the machine's default coding agent
  (`~/.config/omarchy/defaults/agent`) instead of whichever collector sorts
  first alphabetically (Claude).
- Ships Grok mark SVGs for dark and light surfaces.
