from __future__ import annotations

from textual.containers import Container, Horizontal
from textual.widgets import Button, DataTable, Static

def build(app, pane):
    app.mount_topcard(pane, "History", "Logged actions (apply/paccache/etc.)", "Enter Info")
    row = Horizontal(id="hist_row")
    pane.mount(row)

    tbl = DataTable(id="hist_tbl")
    app.safe_cursor_row(tbl)
    tbl.add_columns("ts", "action", "rc", "cmd")

    row.mount(Container(tbl, id="hist_left"))
    row.mount(Static("", id="hist_info", classes="infobox"))

    pane.mount(
        Horizontal(
            Button("Refresh", id="btn_hist_refresh", variant="primary"),
            classes="toolbar",
        )
    )

    refresh(app)

def refresh(app):
    tbl = app.query_one("#hist_tbl", DataTable)
    tbl.clear(columns=True)
    tbl.add_columns("ts", "action", "rc", "cmd")
    for e in app.history[:500]:
        cmd0 = (e.get("cmds") or [""])[0]
        tbl.add_row(str(e.get("ts", "")), str(e.get("action", "")), str(e.get("rc", "")), str(cmd0)[:120])
    app.set_last("History refreshed")

def on_row_highlighted(app, event, table_id: str) -> bool:
    if table_id != "hist_tbl":
        return False
    tbl = event.data_table
    if not tbl.row_count:
        return True
    idx = tbl.cursor_row
    if idx < 0 or idx >= len(app.history):
        return True
    e = app.history[idx]
    cmds = "\n".join(e.get("cmds") or [])
    body = f"[b]{e.get('ts','')}[/b]\nAction: {e.get('action','')}\nrc={e.get('rc','')}\n\n{cmds}"
    app.query_one("#hist_info", Static).update(body[:15000])
    return True

async def on_button(app, bid: str) -> bool:
    if bid == "btn_hist_refresh":
        app.history = __import__("pkgpicker.history", fromlist=["parse_history"]).parse_history(app.HISTORY_LOG)  # minimal import
        refresh(app)
        return True
    return False

