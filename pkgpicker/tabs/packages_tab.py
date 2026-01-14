from __future__ import annotations
from textual.containers import Container, Horizontal
from textual.widgets import Button, DataTable, Static
from typing import Optional

def build(app, pane):
    ui = app.cfg.get("ui", {}) or {}
    t = app.current_target()
    app.mount_topcard(
        pane,
        t.name,
        str(ui.get("tagline", "")),
        "Space Toggle · Enter Info · a Selection→Plan · q QuickAdd · i Apply · / Search · [ ] Target",
    )

    row = Horizontal(id="pkg_row")
    pane.mount(row)

    cat_tbl = DataTable(id="cat_tbl")
    pkg_tbl = DataTable(id="pkg_tbl")
    info = Static("", id="pkg_info", classes="infobox")

    app.safe_cursor_row(cat_tbl)
    app.safe_cursor_row(pkg_tbl)

    cat_tbl.add_columns("Kategorie")
    pkg_tbl.add_columns("Sel", "Pkg", "Src", "Inst", "Hint")

    row.mount(Container(cat_tbl, id="pkg_cat"))
    row.mount(Container(pkg_tbl, id="pkg_list"))
    row.mount(info)

    pane.mount(
        Horizontal(
            Button("Add Selection → Plan (a)", id="btn_add_plan", variant="success"),
            Button("Clear Selection", id="btn_clear_sel", variant="warning"),
            Button("Target → Plan", id="btn_target_to_plan", variant="primary"),
            classes="toolbar",
        )
    )

    refresh(app)

def refresh(app):
    # categories
    cat_tbl = app.query_one("#cat_tbl", DataTable)
    cat_tbl.clear(columns=True)
    cat_tbl.add_columns("Kategorie")

    if not app.categories:
        cat_tbl.add_row("(keine Kategorien in packages.json)")
        _populate_pkg_tbl(app)
        _info(app, None, None)
        return

    for c in app.categories:
        cat_tbl.add_row(c.name, key=c.name)

    app.cat_idx = max(0, min(app.cat_idx, len(app.categories) - 1))
    try:
        cat_tbl.move_cursor(row=app.cat_idx, column=0)
    except Exception:
        pass

    _populate_pkg_tbl(app)
    _info(app, None, None)

def _category_items(app):
    if not app.categories:
        return []
    return app.categories[app.cat_idx].items

def _populate_pkg_tbl(app):
    pkg_tbl = app.query_one("#pkg_tbl", DataTable)
    pkg_tbl.clear(columns=True)
    pkg_tbl.add_columns("Sel", "Pkg", "Src", "Inst", "Hint")

    for it in _category_items(app):
        sel = "✔" if (it.name in app.selected_repo or it.name in app.selected_aur) else ""
        inst = "✔" if it.name in app.installed_all else ""
        hint = it.reason or ("★" if it.featured else "")
        pkg_tbl.add_row(sel, it.name, it.source, inst, hint[:30], key=it.name)

def _info(app, pkg: Optional[str], src: Optional[str]):
    box = app.query_one("#pkg_info", Static)
    if not pkg:
        box.update("[b]Info[/b]\n\nSpace Toggle · Enter Info · a → Plan")
        return
    box.update(f"[b]{pkg}[/b]\n[dim]Quelle:[/dim] {src or ''}")

def on_row_highlighted(app, event, table_id: str) -> bool:
    if table_id == "cat_tbl":
        if not app.categories:
            return True
        app.cat_idx = max(0, min(event.cursor_row, len(app.categories) - 1))
        _populate_pkg_tbl(app)
        return True

    if table_id == "pkg_tbl":
        tbl = event.data_table
        if tbl.row_count:
            row = tbl.get_row_at(tbl.cursor_row)
            _info(app, str(row[1]), str(row[2]))
        return True

    return False

async def on_button(app, bid: str) -> bool:
    if bid == "btn_add_plan":
        app.action_add_plan()
        return True
    if bid == "btn_clear_sel":
        app.selected_repo.clear()
        app.selected_aur.clear()
        _populate_pkg_tbl(app)
        app.update_status()
        app.set_last("Selection cleared")
        return True
    if bid == "btn_target_to_plan":
        t = app.current_target()
        for p in t.required_packages:
            app.plan_repo.add(p)
        for p in t.recommended_packages:
            app.plan_repo.add(p)
        app.set_last("Target → Plan")
        return True
    return False

def _active_pkg_row(app):
    tbl = app.query_one("#pkg_tbl", DataTable)
    if not tbl.row_count:
        return None
    return tbl.get_row_at(tbl.cursor_row)

def action_toggle(app) -> bool:
    # toggles only if pkg_tbl focused
    try:
        if not app.query_one("#pkg_tbl").has_focus:
            return False
    except Exception:
        return False
    row = _active_pkg_row(app)
    if not row:
        return True
    pkg = str(row[1]); src = str(row[2])
    if src == "aur":
        if pkg in app.selected_aur: app.selected_aur.remove(pkg)
        else: app.selected_aur.add(pkg); app.selected_repo.discard(pkg)
    else:
        if pkg in app.selected_repo: app.selected_repo.remove(pkg)
        else: app.selected_repo.add(pkg); app.selected_aur.discard(pkg)
    _populate_pkg_tbl(app)
    app.update_status()
    return True

def action_info(app) -> bool:
    try:
        if not app.query_one("#pkg_tbl").has_focus:
            return False
    except Exception:
        return False
    row = _active_pkg_row(app)
    if row:
        _info(app, str(row[1]), str(row[2]))
    return True

