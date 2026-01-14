from __future__ import annotations
from textual.containers import Container, Horizontal
from textual.widgets import Button, DataTable, Input, Static
from typing import List, Tuple

from ..cache import cached_search

def build(app, pane):
    app.mount_topcard(pane, "Search", "Repo + AUR (cached).", "Space Toggle · Enter Info · q QuickAdd")
    pane.mount(
        Horizontal(
            Input(placeholder="search query…", id="search_input"),
            Button("Repo", id="btn_search_repo", variant="primary"),
            Button("AUR", id="btn_search_aur", variant="primary"),
            Button("Both", id="btn_search_both", variant="success"),
            classes="toolbar",
        )
    )
    row = Horizontal(id="search_row")
    pane.mount(row)

    tbl = DataTable(id="search_tbl")
    app.safe_cursor_row(tbl)
    tbl.add_columns("Sel", "Pkg", "Src", "Inst", "Desc")

    row.mount(Container(tbl, id="search_list"))
    row.mount(Static("[b]Search Info[/b]\n", id="search_info", classes="infobox"))

def focus_input(app):
    try:
        app.query_one("#search_input", Input).focus()
    except Exception:
        pass

def _populate(app, rows: List[Tuple[str, str, str]]):
    tbl = app.query_one("#search_tbl", DataTable)
    tbl.clear(columns=True)
    tbl.add_columns("Sel", "Pkg", "Src", "Inst", "Desc")
    for name, src, desc in rows:
        sel = "✔" if (name in app.selected_repo or name in app.selected_aur) else ""
        inst = "✔" if name in app.installed_all else ""
        tbl.add_row(sel, name, src, inst, desc[:90], key=f"{src}:{name}")

def _do_search(app, mode: str, query: str):
    query = query.strip()
    if not query:
        app.call_from_thread(app.set_last, "Search: empty")
        return

    rows: List[Tuple[str, str, str]] = []
    if mode in ("repo", "both"):
        for r in cached_search(app.SEARCH_CACHE_FILE, "repo", query):
            rows.append((r["name"], "repo", r.get("desc", "")))
    if mode in ("aur", "both"):
        for r in cached_search(app.SEARCH_CACHE_FILE, "aur", query):
            rows.append((r["name"], "aur", r.get("desc", "")))

    seen = set()
    out = []
    for n, s, d in rows:
        if n in seen: continue
        seen.add(n); out.append((n, s, d))

    def _ui():
        _populate(app, out)
        app.set_last(f"Search: {len(out)} results ({mode})")
    app.call_from_thread(_ui)

async def on_button(app, bid: str) -> bool:
    if bid in ("btn_search_repo", "btn_search_aur", "btn_search_both"):
        mode = "repo" if bid == "btn_search_repo" else ("aur" if bid == "btn_search_aur" else "both")
        q = app.query_one("#search_input", Input).value
        def worker():
            app.call_from_thread(app.set_busy, "Search …")
            _do_search(app, mode, q)
            app.call_from_thread(app.set_busy, "")
        import threading
        threading.Thread(target=worker, daemon=True).start()
        return True
    return False

def on_row_highlighted(app, event, table_id: str) -> bool:
    if table_id != "search_tbl":
        return False
    tbl = event.data_table
    if tbl.row_count:
        row = tbl.get_row_at(tbl.cursor_row)
        app.query_one("#search_info", Static).update(f"[b]{row[1]}[/b] [{row[2]}]\n\n{row[4]}")
    return True

def action_toggle(app) -> bool:
    try:
        if not app.query_one("#search_tbl").has_focus:
            return False
    except Exception:
        return False
    tbl = app.query_one("#search_tbl", DataTable)
    if not tbl.row_count:
        return True
    row = tbl.get_row_at(tbl.cursor_row)
    pkg, src = str(row[1]), str(row[2])
    if src == "aur":
        if pkg in app.selected_aur: app.selected_aur.remove(pkg)
        else: app.selected_aur.add(pkg); app.selected_repo.discard(pkg)
    else:
        if pkg in app.selected_repo: app.selected_repo.remove(pkg)
        else: app.selected_repo.add(pkg); app.selected_aur.discard(pkg)
    app.set_last("Toggled search selection")
    return True

def action_info(app) -> bool:
    try:
        if not app.query_one("#search_tbl").has_focus:
            return False
    except Exception:
        return False
    return True

