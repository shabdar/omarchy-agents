#!/usr/bin/python3
"""Collect SuperGrok usage into one Omarchy agents-panel JSON record.

Omarchy's bar plugin (`ali.agents`, cloned from `omarchy.agents`) never talks
to provider APIs itself. It only reads JSON files from:

    ~/.local/state/omarchy/agents/usage/<agent>.json

Stock Omarchy ships collectors for Claude, Codex, and Fireworks. This script
is the Grok collector: it prints one record on stdout. `refresh-usage.sh`
writes that stdout to `grok.json`.

What it measures
----------------
The SuperGrok *shared weekly usage pool* — the same percentage shown in
grok.com → Settings → Usage — via the Grok Build CLI billing endpoint:

    GET https://cli-chat-proxy.grok.com/v1/billing?format=credits
    GET https://cli-chat-proxy.grok.com/v1/settings

Auth comes from the local Grok Build login (`~/.grok/auth.json`). The
access token is used in-memory. If it has expired, this script tries a
refresh-token grant against auth.x.ai and does **not** write tokens back
to `auth.json` (Grok CLI owns that file).

Flags (same shape as Omarchy's other collectors)
------------------------------------------------
--force         Ignore the 15s limits cache and re-probe the network.
--limits-only   Accepted for CLI compatibility; Grok has no local
                transcript scan, so this is the same as a normal run.
--except grok   Exit 0 without printing a record.
<agent...>      If any agent names are given, only run when `grok` is listed.

The panel expects `limits[].percent` as a 0..1 fraction, not 0..100.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

AGENT_ID = "grok"
AGENT_NAME = "Grok"
AUTH_HELP = "Run `grok login` to restore SuperGrok usage."
BILLING_URL = "https://cli-chat-proxy.grok.com/v1/billing?format=credits"
SETTINGS_URL = "https://cli-chat-proxy.grok.com/v1/settings"
TOKEN_URL = "https://auth.x.ai/oauth2/token"
PROBE_MIN_INTERVAL_SECONDS = 15


def grok_home() -> Path:
  """Grok Build's data directory (`$GROK_HOME`, else `~/.grok`)."""
  return Path(os.environ.get("GROK_HOME") or (Path.home() / ".grok")).expanduser()


def cache_root() -> Path:
  """Where this collector caches the last successful limits probe."""
  root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "omarchy" / "agent-usage"
  root.mkdir(parents=True, exist_ok=True)
  return root


def parse_iso(raw: str) -> dt.datetime | None:
  """Parse an ISO-8601 timestamp, including values with >6 fractional digits."""
  text = str(raw or "").strip()
  if not text:
    return None
  text = text.replace("Z", "+00:00")
  if "." in text:
    head, rest = text.split(".", 1)
    frac = ""
    tz = ""
    for i, ch in enumerate(rest):
      if ch.isdigit():
        frac += ch
      else:
        tz = rest[i:]
        break
    text = head + "." + frac[:6].ljust(6, "0") + tz
  try:
    parsed = dt.datetime.fromisoformat(text)
  except ValueError:
    return None
  if parsed.tzinfo is None:
    parsed = parsed.replace(tzinfo=dt.timezone.utc)
  return parsed


def empty_stats() -> dict[str, Any]:
  """Local token charts stay empty: Grok session files do not expose billed tokens."""
  return {
    "todayPrompts": 0,
    "todaySessions": 0,
    "todayTotalTokens": 0,
    "todayTokensByModel": {},
    "recentDays": [],
    "totalPrompts": 0,
    "totalSessions": 0,
    "activeDays": 0,
    "activeDates": [],
    "modelUsage": {},
    "hasLocalStats": False,
    "hasPromptStats": False,
  }


def oidc_record(auth: dict[str, Any]) -> dict[str, Any] | None:
  """Pick the SpaceXAI OIDC login from `~/.grok/auth.json`."""
  best = None
  for value in auth.values():
    if not isinstance(value, dict):
      continue
    if value.get("auth_mode") != "oidc":
      continue
    if not str(value.get("key") or ""):
      continue
    best = value
    issuer = str(value.get("oidc_issuer") or "")
    if "auth.x.ai" in issuer:
      return value
  return best


def token_expired(record: dict[str, Any], skew_seconds: int = 60) -> bool:
  expires = parse_iso(str(record.get("expires_at") or ""))
  if expires is None:
    return False
  return expires <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=skew_seconds)


def refresh_access_token(record: dict[str, Any]) -> str:
  """Exchange the stored refresh token for a new access token. Never writes disk."""
  refresh = str(record.get("refresh_token") or "")
  client_id = str(record.get("oidc_client_id") or "")
  if not refresh or not client_id:
    return ""
  body = urllib.parse.urlencode({
    "grant_type": "refresh_token",
    "refresh_token": refresh,
    "client_id": client_id,
  }).encode("utf-8")
  request = urllib.request.Request(
    TOKEN_URL,
    data=body,
    method="POST",
    headers={
      "Content-Type": "application/x-www-form-urlencoded",
      "Accept": "application/json",
    },
  )
  try:
    with urllib.request.urlopen(request, timeout=10) as response:
      payload = json.loads(response.read().decode("utf-8", errors="replace"))
  except Exception:
    return ""
  return str(payload.get("access_token") or "")


def access_token() -> tuple[str, str]:
  """Return `(token, status)` where status is `ok`, `expired`, or `missing`."""
  path = grok_home() / "auth.json"
  try:
    auth = json.loads(path.read_text(encoding="utf-8"))
  except Exception:
    return "", "missing"
  if not isinstance(auth, dict):
    return "", "missing"
  record = oidc_record(auth)
  if record is None:
    return "", "missing"
  token = str(record.get("key") or "")
  if token and not token_expired(record):
    return token, "ok"
  refreshed = refresh_access_token(record)
  if refreshed:
    return refreshed, "ok"
  if token:
    return token, "expired"
  return "", "missing"


def http_json(url: str, token: str) -> tuple[dict[str, Any] | None, str]:
  """GET JSON with the Grok Build CLI bearer headers."""
  request = urllib.request.Request(
    url,
    headers={
      "Authorization": "Bearer " + token,
      "x-xai-token-auth": "xai-grok-cli",
      "Accept": "application/json",
      "User-Agent": "omarchy-agent-usage-grok/1",
    },
    method="GET",
  )
  try:
    with urllib.request.urlopen(request, timeout=10) as response:
      payload = json.loads(response.read().decode("utf-8", errors="replace"))
  except urllib.error.HTTPError as error:
    return None, f"http-{error.code}"
  except Exception:
    return None, "transport"
  if not isinstance(payload, dict):
    return None, "shape"
  return payload, "ok"


def period_title(period_type: str) -> str:
  text = str(period_type or "").upper()
  if "MONTH" in text:
    return "Monthly"
  if "DAY" in text and "7" not in text and "WEEK" not in text:
    return "Daily"
  return "Weekly"


def period_label(title: str) -> str:
  if title == "Monthly":
    return "Monthly (30-day)"
  if title == "Daily":
    return "Daily"
  return "Weekly (7-day)"


def money_val(raw: Any) -> float | None:
  if isinstance(raw, dict) and "val" in raw:
    raw = raw.get("val")
  try:
    value = float(raw)
  except (TypeError, ValueError):
    return None
  if value != value:
    return None
  return value


def limits_from_billing(payload: dict[str, Any]) -> list[dict[str, Any]]:
  """Turn a billing payload into the panel's `limits` array. Percent is 0..1."""
  config = payload.get("config") if isinstance(payload.get("config"), dict) else payload
  percent = config.get("creditUsagePercent")
  if percent is None:
    used = money_val(config.get("onDemandUsed"))
    cap = money_val(config.get("onDemandCap"))
    if used is not None and cap and cap > 0:
      percent = used / cap * 100.0
  try:
    fraction = float(percent) / 100.0
  except (TypeError, ValueError):
    return []
  if fraction != fraction or fraction < 0:
    return []
  period = config.get("currentPeriod") if isinstance(config.get("currentPeriod"), dict) else {}
  title = period_title(str(period.get("type") or ""))
  reset = str(period.get("end") or config.get("billingPeriodEnd") or "")
  return [{
    "label": period_label(title),
    "title": title,
    "percent": min(max(fraction, 0.0), 1.0),
    "resetsAt": reset,
  }]


def collect_limits(token: str, token_status: str, force: bool) -> dict[str, Any]:
  """Probe billing + settings, reusing a short-lived cache and last-known limits."""
  result = {
    "limits": [],
    "tierLabel": "",
    "usageStatusText": "",
    "authHelpText": AUTH_HELP,
  }
  cache_file = cache_root() / "grok-limits.json"
  cached: dict[str, Any] = {}
  try:
    cached = json.loads(cache_file.read_text(encoding="utf-8"))
    if not isinstance(cached, dict):
      cached = {}
  except Exception:
    cached = {}
  fallback = cached.get("limits") if isinstance(cached.get("limits"), list) else []

  if token_status == "missing" or token == "":
    result["limits"] = fallback
    result["tierLabel"] = str(cached.get("tierLabel") or "")
    result["usageStatusText"] = "Waiting for auth"
    return result

  fetched_at = 0.0
  try:
    fetched_at = float(cached.get("fetchedAtMs") or 0) / 1000.0
  except (TypeError, ValueError):
    fetched_at = 0.0
  if fallback and not force and fetched_at and (dt.datetime.now().timestamp() - fetched_at) < PROBE_MIN_INTERVAL_SECONDS:
    result["limits"] = fallback
    result["tierLabel"] = str(cached.get("tierLabel") or "")
    return result

  billing, billing_status = http_json(BILLING_URL, token)
  if billing_status == "transport":
    result["limits"] = fallback
    result["tierLabel"] = str(cached.get("tierLabel") or "")
    result["retryAdvised"] = True
    if not fallback:
      result["usageStatusText"] = "Grok limits unavailable"
      result["authHelpText"] = "Couldn't reach Grok's usage endpoint. Retrying shortly."
    return result
  if billing is None:
    result["limits"] = fallback
    result["tierLabel"] = str(cached.get("tierLabel") or "")
    if token_status == "expired" or billing_status == "http-401":
      result["usageStatusText"] = "Sign-in expired"
      result["authHelpText"] = "Grok's saved sign-in expired. Run `grok login` to refresh it."
    elif not fallback:
      result["usageStatusText"] = "Grok limits unavailable"
      result["authHelpText"] = "Grok's usage endpoint did not return limits. Run `grok login` if this persists."
    return result

  limits = limits_from_billing(billing)
  settings, _settings_status = http_json(SETTINGS_URL, token)
  tier = ""
  if isinstance(settings, dict):
    tier = str(settings.get("subscription_tier_display") or "")
  if not tier:
    tier = str(cached.get("tierLabel") or "SuperGrok")

  result["limits"] = limits
  result["tierLabel"] = tier
  try:
    cache_file.write_text(
      json.dumps({"fetchedAtMs": round(dt.datetime.now().timestamp() * 1000), "limits": limits, "tierLabel": tier})
      + "\n",
      encoding="utf-8",
    )
  except Exception:
    pass
  if not limits:
    result["usageStatusText"] = "Grok limits unavailable"
    result["authHelpText"] = "Grok's usage endpoint returned no weekly pool."
  return result


def main() -> int:
  parser = argparse.ArgumentParser(description="Print the Grok SuperGrok usage record as JSON")
  parser.add_argument("--force", action="store_true", help="ignore the limits cache and re-probe")
  parser.add_argument("--limits-only", action="store_true", help="accepted for compatibility with the panel")
  parser.add_argument("--except", dest="except_agent", action="append", default=[], help="skip when grok is listed")
  parser.add_argument("agents", nargs="*", help="if given, only run when grok is in the list")
  args, _unknown = parser.parse_known_args()
  if AGENT_ID in args.except_agent:
    return 0
  if args.agents and AGENT_ID not in args.agents:
    return 0

  token, token_status = access_token()
  limits = collect_limits(token, token_status, args.force)
  stats = empty_stats()
  record = {
    "schemaVersion": 1,
    "id": AGENT_ID,
    "name": AGENT_NAME,
    "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
    "ready": len(limits["limits"]) > 0,
    "tierLabel": limits["tierLabel"],
    "usageStatusText": limits["usageStatusText"],
    "authHelpText": limits["authHelpText"],
    "limits": limits["limits"],
  }
  if limits.get("retryAdvised"):
    record["retryAdvised"] = True
  record.update(stats)
  json.dump(record, sys.stdout, separators=(",", ":"))
  sys.stdout.write("\n")
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except Exception as exc:
    print(f"omarchy-agent-usage-grok: {exc}", file=sys.stderr)
    raise SystemExit(1)
