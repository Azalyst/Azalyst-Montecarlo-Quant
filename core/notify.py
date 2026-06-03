"""Discord webhook notifications (rich embeds + user ping)."""
from __future__ import annotations
import os
import requests
from .models import Signal, Position
from .state import Book

GREEN = 0x2ECC71
RED = 0xE74C3C
BLUE = 0x3498DB
ORANGE = 0xE67E22


class Notifier:
    def __init__(self, webhook_url: str | None, user_id: str, dry_run: bool = False):
        self.url = webhook_url
        self.user_id = user_id
        self.dry_run = dry_run or not webhook_url

    def _send(self, content: str, embed: dict):
        if self.dry_run:
            print(f"[DRY-RUN discord] {content}\n  {embed.get('title')} :: "
                  + " | ".join(f"{f['name']}={f['value']}" for f in embed.get("fields", [])))
            return
        payload = {
            "content": content,
            "embeds": [embed],
            "allowed_mentions": {"users": [self.user_id]},
            "username": "Azalyst FundingPips",
        }
        try:
            r = requests.post(self.url, json=payload, timeout=15)
            if r.status_code >= 300:
                print(f"[discord] HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"[discord] send failed: {e}")

    def _acct_footer(self, acc: Book) -> dict:
        return {"text": (f"[{acc.strategy} book / {acc.status}] Equity ${acc.equity:,.0f} | "
                         f"Day PnL ${acc.daily_realized_pnl:,.0f} | Bal ${acc.balance:,.0f} | "
                         f"W/L {acc.wins}/{acc.losses}")}

    def signal(self, sig: Signal, pos: Position, acc: Book):
        color = GREEN if sig.side == "BUY" else RED
        arrow = "▲ BUY" if sig.side == "BUY" else "▼ SELL"
        fields = [
            {"name": "Direction", "value": arrow, "inline": True},
            {"name": "Entry", "value": f"{sig.entry:g}", "inline": True},
            {"name": "RR", "value": f"1:{sig.compute_rr():g}", "inline": True},
            {"name": "Stop", "value": f"{sig.stop:g}", "inline": True},
            {"name": "Target", "value": f"{sig.target:g}", "inline": True},
            {"name": "Risk", "value": f"${pos.risk_usd:,.0f}", "inline": True},
            {"name": "Size", "value": f"{pos.lots:g} lots ({pos.units:,.0f} u)", "inline": True},
            {"name": "Daily loss left", "value": f"${max(0.0, 5000 - (acc.today_start_equity - acc.equity)):,.0f}", "inline": True},
            {"name": "Max loss left", "value": f"${max(0.0, acc.equity - 90000):,.0f}", "inline": True},
        ]
        if sig.note:
            fields.append({"name": "Setup", "value": sig.note[:240], "inline": False})
        embed = {
            "title": f"{sig.strategy.upper()} - {sig.symbol} ({sig.interval})",
            "color": color, "fields": fields, "footer": self._acct_footer(acc),
        }
        self._send(f"<@{self.user_id}> new **{sig.side}** signal on **{sig.symbol}**", embed)

    def close(self, pos: Position, acc: Book):
        win = pos.pnl_usd >= 0
        embed = {
            "title": f"CLOSED {pos.strategy.upper()} - {pos.symbol} [{pos.exit_reason.upper()}]",
            "color": GREEN if win else RED,
            "fields": [
                {"name": "Side", "value": pos.side, "inline": True},
                {"name": "Entry", "value": f"{pos.entry:g}", "inline": True},
                {"name": "Exit", "value": f"{pos.exit_price:g}", "inline": True},
                {"name": "PnL", "value": f"${pos.pnl_usd:,.2f}", "inline": True},
                {"name": "R", "value": f"{pos.r_multiple:+g}R", "inline": True},
            ],
            "footer": self._acct_footer(acc),
        }
        self._send(f"<@{self.user_id}> trade closed: **{pos.symbol}** "
                   f"**${pos.pnl_usd:,.2f}** ({pos.r_multiple:+g}R)", embed)

    def alert(self, title: str, message: str, color: int = ORANGE):
        embed = {"title": title, "description": message, "color": color}
        self._send(f"<@{self.user_id}> {title}", embed)
