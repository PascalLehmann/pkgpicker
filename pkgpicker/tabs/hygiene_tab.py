from __future__ import annotations

import threading
from textual.containers import Horizontal
from textual.widgets import Button, Static

from ..arch import pacman_orphans, paccache_clean, which
from ..history import log_history

def build(app, pane):
    app.mount_topcard(pane, "Hygiene", "Orphans + pacman cache cleanup", "Use with care.")
    pane.mount(
        Horizontal(
            Button("List orphans", id="btn_hyg_orphans", variant="primary"),
            Button("Add orphans → Remove plan", id="btn_hyg_add_rm", variant="warning"),
            Button("paccache -r", id="btn_hyg_paccache", variant="success"),
            classes="toolbar",
        )
    )
    pane.mount(Static("", id="hyg_out", classes="infobox"))
    _render(app)

def _render(app):
    box = app.query_one("#hyg_out", Static)
    orph = pacman_orphans()
    body = [
        f"[b]Orphans[/b]: {len(orph)}",
        " ".join(orph[:120]) + (" ..." if len(orph) > 120 else ""),
        "",
        f"paccache available: {'YES' if which('paccache') else 'no'}",
    ]
    box.update("\n".join(body))
    app._orph_cache = orph  # type: ignore[attr-defined]

def _paccache_worker(app):
    app.call_from_thread(app.set_busy, "Running paccache …")
    rc, out = paccache_clean()
    log_history(app.HISTORY_LOG, "paccache", ["sudo paccache -r"], rc)
    app.call_from_thread(app.set_busy, "")
    app.call_from_thread(app.show_output, "paccache", f"rc={rc}\n\n{out[-12000:]}")
    app.call_from_thread(app.set_last, f"paccache rc={rc}")

async def on_button(app, bid: str) -> bool:
    if bid == "btn_hyg_orphans":
        _render(app)
        app.set_last("Orphans refreshed")
        return True
    if bid == "btn_hyg_add_rm":
        orph = getattr(app, "_orph_cache", []) or pacman_orphans()
        for p in orph:
            app.remove_explicit.add(p)
        app.set_last(f"Added {len(orph)} orphans to remove plan")
        return True
    if bid == "btn_hyg_paccache":
        ok = await app.ask_confirm("paccache -r", "Pacman cache cleanup ausführen?")
        if not ok:
            return True
        threading.Thread(target=_paccache_worker, args=(app,), daemon=True).start()
        return True
    return False

