from __future__ import annotations
from textual.widgets import Static
from ..arch import which

def build(app, pane):
    app.mount_topcard(pane, "Self-Check", "prüft Tools & optional deps", "")
    pane.mount(
        Static(
            f"yay: {'OK' if which('yay') else 'MISSING'} · "
            f"expac: {'OK' if which('expac') else 'MISSING'} · "
            f"paccache: {'OK' if which('paccache') else 'MISSING'} · "
            f"lspci: {'OK' if which('lspci') else 'MISSING'}",
            classes="infobox",
        )
    )

async def on_button(app, bid: str) -> bool:
    return False

