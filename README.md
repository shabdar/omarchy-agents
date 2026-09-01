# shabdar.agents — Omarchy AI usage meters (v2.0.0)

An [Omarchy](https://omarchy.org/) status-bar plugin that shows rate-limit **meters** for the AI coding agents on the machine. Clicking the AI icon opens **your default agent first** (Grok, if that is what you chose), not Claude.

**Version:** 2.0.0
**Plugin id:** `shabdar.agents` (same on every machine — not your Linux username)
**License:** MIT (see [LICENSE](LICENSE))

## Plugin id

`omarchy plugin clone omarchy.agents` names the copy `<linux-user>.agents`. That was this machine’s v1 path (`ali.agents`).

A GitHub plugin is different. `omarchy plugin add <git-url>` installs into `~/.config/omarchy/plugins/<manifest.id>/`. The id is a **publisher id**, the same way Omarchy’s docs use `acme.weather`. Everyone who adds this repo gets `shabdar.agents`. Their `$USER` is never read.

IPC stays `omarchy.agents` (see `clonedFrom` in the manifest).

## Install

```bash
omarchy plugin add https://github.com/shabdar/omarchy-agents.git --yes
cd ~/.config/omarchy/plugins/shabdar.agents
chmod +x setup.sh collect-grok.py refresh-usage.sh
./setup.sh
omarchy plugin enable shabdar.agents --section right --yes
omarchy plugin disable omarchy.agents --yes
grok login
./refresh-usage.sh --force
omarchy restart shell
```

If you previously cloned the built-in widget (`$USER.agents` or `ali.agents`), disable or remove that clone so you do not have two Agents buttons.

Update: `omarchy plugin update shabdar.agents`

## What you should see

On a signed-in Grok machine whose default agent is Grok:

1. Click the AI icon (same popup chrome as v1).
2. Hero reads **Grok** / **SuperGrok**.
3. **SUPERGROK** weekly pool % + reset, then Chat / Imagine / Voice / Build of that same pool (`—` if unknown).
4. **GROK BOT** is a separate weekly meter (never merged). Overlay-only until xAI publishes an API.
5. **ACCOUNT**: credits $, on-demand, status (`ok` | `pool exhausted` | `rate-limited`), last job (Chat|Bot|Build), SuperGrok **subscription** billing-period end.

Optional overlay: copy `grok.example.json` to `~/.config/omarchy/agents/grok.json`. Non-null keys win. Do not invent quotas.

See [CHANGELOG.md](CHANGELOG.md) for the full v2.0.0 notes.
