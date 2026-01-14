from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from textual.containers import Container, Horizontal
from textual.widgets import Button, DataTable, Static

from ..arch import systemctl_is_active, systemctl_is_enabled

def _normalize_unit(u: Any) -> str:
    unit = ""
    if isinstance(u, str):
        unit = u.strip()
    elif isinstance(u, dict):
        unit = str(u.get("unit") or u.get("name") or u.get("service") or "").strip()
    else:
        unit = str(u).strip()
    if not unit:
        return ""
    if not unit.endswith(".service") and "." not in unit:
        unit += ".service"
    return unit

def _desc(u: Any) -> str:
    if isinstance(u, dict):
        return str(u.get("desc") or u.get("why") or u.get("reason") or "").strip()
    return ""

def build(app, pane):
    app.mount_topcard(pane, "Services", "systemd status + enable/disable planning (applied in Plan → Apply)", "Space Toggle(plan) · Enter Info")
    row = Horizontal(id="svc_row")
    pane.mount(row)

    tbl = DataTable(id="svc_tbl")
    app.safe_cursor_row(tbl)
    tbl.add_columns("Plan", "Unit", "enabled", "active", "desc")

    row.mount(Container(tbl, id="svc_left"))
    row.mount(Static("", id="svc_info", classes="infobox"))

    pane.mount(
        Horizontal(
            Button("Refresh", id="btn_svc_refresh", variant="primary"),
            Button("Plan Enable", id="btn_svc_en", variant="success"),
            Button("Plan Disable", id="btn_svc_dis", variant="warning"),
            Button("Clear svc plan", id="btn_svc_clear", variant="warning"),
            classes="toolbar",
        )
    )
    refresh(app)

def _service_sources(app) -> List[Any]:
    # Combine cfg services + target services + a few essentials
    raw = []
    raw.extend(list(app.cfg.get("services", []) or []))
    raw.extend(list(app.current_target().services or []))
    essentials = [
        {"name": "greetd", "desc": "Greeter daemon (tuigreet)"},
        {"name": "NetworkManager", "desc": "Network"},
        {"name": "bluetooth", "desc": "Bluetooth (bluez)"},
        {"name": "cups", "desc": "Printing"},
        {"name": "avahi-daemon", "desc": "mDNS/Bonjour"},
    ]
    raw = essentials + raw
    return raw

def refresh(app):
    tbl = app.query_one("#svc_tbl", DataTable)
    tbl.clear(columns=True)
    tbl.add_columns("Plan", "Unit", "enabled", "active", "desc")

    seen: Set[str] = set()
    entries: List[Tuple[str, str]] = []

    for u in _service_sources(app):
        unit = _normalize_unit(u)
        if not unit or unit in seen:
            continue
        seen.add(unit)
        entries.append((unit, _desc(u)))

    for unit, desc in entries:
        en = systemctl_is_enabled(unit)
        ac = systemctl_is_active(unit)
        plan = ""
        if unit in app.plan_services_enable:
            plan = "enable"
        elif unit in app.plan_services_disable:
            plan = "disable"
        tbl.add_row(plan, unit, en, ac, desc[:80], key=unit)

    app.set_last("Services refreshed")
    app.update_status()

def _current_unit(app) -> str:
    tbl = app.query_one("#svc_tbl", DataTable)
    if not tbl.row_count:
        return ""
    return str(tbl.get_row_at(tbl.cursor_row)[1])

def on_row_highlighted(app, event, table_id: str) -> bool:
    if table_id != "svc_tbl":
        return False
    tbl = event.data_table
    if not tbl.row_count:
        return True
    row = tbl.get_row_at(tbl.cursor_row)
    body = (
        f"[b]{row[1]}[/b]\n"
        f"enabled: {row[2]}\n"
        f"active: {row[3]}\n\n"
        f"{row[4]}"
    )
    app.query_one("#svc_info", Static).update(body)
    return True

def action_toggle(app) -> bool:
    # space toggles between enable/disable/none
    try:
        if not app.query_one("#svc_tbl").has_focus:
            return False
    except Exception:
        return False
    unit = _current_unit(app)
    if not unit:
        return True
    if unit in app.plan_services_enable:
        app.plan_services_enable.remove(unit)
        app.plan_services_disable.add(unit)
    elif unit in app.plan_services_disable:
        app.plan_services_disable.remove(unit)
    else:
        app.plan_services_enable.add(unit)
    refresh(app)
    app.set_last(f"Toggled svc plan: {unit}")
    return True

def action_info(app) -> bool:
    return False

async def on_button(app, bid: str) -> bool:
    if bid == "btn_svc_refresh":
        refresh(app)
        return True
    if bid == "btn_svc_en":
        unit = _current_unit(app)
        if unit:
            app.plan_services_enable.add(unit)
            app.plan_services_disable.discard(unit)
            refresh(app)
        return True
    if bid == "btn_svc_dis":
        unit = _current_unit(app)
        if unit:
            app.plan_services_disable.add(unit)
            app.plan_services_enable.discard(unit)
            refresh(app)
        return True
    if bid == "btn_svc_clear":
        app.plan_services_enable.clear()
        app.plan_services_disable.clear()
        refresh(app)
        app.set_last("Service plan cleared")
        return True
    return False

