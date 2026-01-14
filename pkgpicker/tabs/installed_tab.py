from __future__ import annotations

import csv
import os
import threading
import time
from typing import Dict, List, Tuple

from textual.containers import Container, Horizontal
from textual.widgets import Button, DataTable, Static

from ..cache import pkginfo_installed
from ..arch import run_capture

def build(app, pane):
    app.mount_topcard(pane, "Installed", "Explizit installierte Pakete (ohne Dependencies) + Infos + Remove + Export", "Space Toggle(Remove) · x Export CSV")
    row = Horizontal(id="inst_row")
    pane.mount(row)

    tbl = DataTable(id="inst_tbl")
    app.safe_cursor_row(tbl)
    tbl.add_columns("RM", "Pkg", "Src", "Ver", "Desc")

    row.mount(Container(tbl, id="inst_left"))
    row.mount(Static("", id="inst_info", classes="infobox"))

    pane.mount(
        Horizontal(
            Button("Refresh", id="btn_inst_refresh", variant="primary"),
            Button("Mark selected → Remove", id="btn_inst_mark_rm", variant="warning"),
            Button("Clear remove marks", id="btn_inst_clear_rm", variant="warning"),
            Button("Export CSV (x)", id="btn_inst_export", variant="success"),
            classes="toolbar",
        )
    )

    refresh(app)

def _src_for_pkg(app, pkg: str) -> str:
    # heuristic: foreign -> aur, else repo
    return "aur" if pkg in app.installed_foreign else "repo"

def refresh(app):
    tbl = app.query_one("#inst_tbl", DataTable)
    tbl.clear(columns=True)
    tbl.add_columns("RM", "Pkg", "Src", "Ver", "Desc")

    # show up to 2500 explicit packages
    for p in app.installed_explicit[:2500]:
        src = _src_for_pkg(app, p)
        info = pkginfo_installed(app.PKGINFO_CACHE_FILE, p)
        ver = info.get("ver", "")
        desc = (info.get("desc", "") or "")[:80]
        rm = "✔" if p in app.remove_explicit else ""
        tbl.add_row(rm, p, src, ver, desc, key=p)

    app.set_last("Installed loaded")
    if tbl.row_count:
        try:
            tbl.cursor_row = 0
        except Exception:
            pass
    

def _selected_pkg(app) -> str:
    tbl = app.query_one("#inst_tbl", DataTable)
    if not tbl.row_count:
        return ""
    return str(tbl.get_row_at(tbl.cursor_row)[1])

def on_row_highlighted(app, event, table_id: str) -> bool:
    if table_id != "inst_tbl":
        return False
    p = _selected_pkg(app)
    if not p:
        return True
    info = pkginfo_installed(app.PKGINFO_CACHE_FILE, p)
    src = _src_for_pkg(app, p)
    body = (
        f"[b]{p}[/b]\n"
        f"Quelle: {src}\n"
        f"Version: {info.get('ver','')}\n"
        f"Repo: {info.get('repo','')}\n\n"
        f"{info.get('desc','')}"
    )
    app.query_one("#inst_info", Static).update(body)
    return True

def action_toggle(app) -> bool:
    try:
        if not app.query_one("#inst_tbl").has_focus:
            return False
    except Exception:
        return False
    p = _selected_pkg(app)
    if not p:
        return True
    # only explicit packages are listed → safe to mark for removal
    if p in app.remove_explicit:
        app.remove_explicit.remove(p)
    else:
        app.remove_explicit.add(p)
    refresh(app)
    app.update_status()
    return True

def action_info(app) -> bool:
    return False

def _export_worker(app, out_path: str) -> None:
    # export list of explicit packages with src + info
    rows: List[Tuple[str, str, str]] = []
    for p in app.installed_explicit:
        src = "aur" if p in app.installed_foreign else "repo"
        info = pkginfo_installed(app.PKGINFO_CACHE_FILE, p)
        desc = info.get("desc", "")
        rows.append((p, src, desc))

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["package", "source", "description"])
        for r in rows:
            w.writerow(r)

    app.call_from_thread(app.show_output, "Export CSV", f"Exported:\n{out_path}")
    app.call_from_thread(app.set_last, "Exported CSV")

async def export_csv(app):
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_path = os.path.join(app.EXPORTS_DIR, f"installed-explicit-{ts}.csv")
    app.set_busy("Exporting CSV …")
    def worker():
        _export_worker(app, out_path)
        app.call_from_thread(app.set_busy, "")
    threading.Thread(target=worker, daemon=True).start()

async def on_button(app, bid: str) -> bool:
    if bid == "btn_inst_refresh":
        app.refresh_all()
        refresh(app)
        app.set_last("Installed refreshed")
        return True
    if bid == "btn_inst_mark_rm":
        # already in remove_explicit via toggle; this is a shortcut (no-op)
        app.set_last("Use Space to mark removals; Apply in Plan tab")
        return True
    if bid == "btn_inst_clear_rm":
        app.remove_explicit.clear()
        refresh(app)
        app.set_last("Remove marks cleared")
        return True
    if bid == "btn_inst_export":
        await export_csv(app)
        return True
    return False


