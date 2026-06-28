"""Discord webhook alerts (optional). Silent no-op if no webhook is configured,
so the engine runs fine without Discord."""
from __future__ import annotations
import os
import requests

GREEN = 0x2ECC71; RED = 0xE74C3C; BLUE = 0x3498DB; ORANGE = 0xE67E22; GOLD = 0xF1C40F


class Notifier:
    def __init__(self, cfg: dict):
        self.url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
        d = cfg.get("discord", {})
        self.user_id = str(d.get("user_id", ""))
        self.enabled = bool(d.get("enabled", True)) and bool(self.url)

    def _send(self, content: str, embed: dict):
        if not self.enabled:
            print(f"[discord dry] {embed.get('title','')}: "
                  + " ".join(f"{f['name']}={f['value']}" for f in embed.get("fields", [])))
            return
        payload = {"content": content, "embeds": [embed],
                   "allowed_mentions": {"users": [self.user_id] if self.user_id else []},
                   "username": "Azalyst Montecarlo Quant"}
        try:
            r = requests.post(self.url, json=payload, timeout=15)
            if r.status_code >= 300:
                print(f"[discord] HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"[discord] send failed: {e}")

    def _ping(self) -> str:
        return f"<@{self.user_id}> " if self.user_id else ""

    def event(self, ev, state: dict):
        """ev is an engine.challenge.Event."""
        color = {"opened": GREEN if "BUY" in ev.title else RED, "closed": BLUE,
                 "phase_pass": GOLD, "bust": RED, "brake": ORANGE}.get(ev.kind, ORANGE)
        if ev.kind == "opened":
            d = ev.data
            try:
                fields = [
                    {"name": "Side", "value": d["side"], "inline": True},
                    {"name": "Entry", "value": f"{d['entry']}", "inline": True},
                    {"name": "Stop", "value": f"{d['stop']}", "inline": True},
                    {"name": "Target", "value": f"{d['target']}", "inline": True},
                    {"name": "Size", "value": f"{d['lots']} lots", "inline": True},
                    {"name": "Risk", "value": f"${d['risk_usd']:,.0f} ({d['risk_pct']}%)", "inline": True},
                ]
                embed = {"title": ev.title, "color": color, "fields": fields,
                         "footer": {"text": _footer(state)}}
                self._send(self._ping() + f"**{d['side']}** signal — {ev.title}", embed)
            except KeyError:
                embed = {"title": ev.title, "description": ev.detail, "color": color,
                         "footer": {"text": _footer(state)}}
                self._send(self._ping() + ev.title, embed)
        else:
            embed = {"title": ev.title, "description": ev.detail, "color": color,
                     "footer": {"text": _footer(state)}}
            self._send(self._ping() + ev.title, embed)

    def test(self):
        self._send(self._ping() + "Azalyst Montecarlo Quant connectivity test",
                   {"title": "✅ Online", "description": "Webhook reachable.", "color": GREEN})


def _footer(state: dict) -> str:
    return (f"{state['phase'].upper()} | Bal ${state['balance']:,.0f} | "
            f"Eq ${state['equity']:,.0f} | day {state.get('day_key','-')}")
