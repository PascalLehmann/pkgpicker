from __future__ import annotations
from textual.widgets import Markdown

def build(app, pane):
    app.mount_topcard(pane, "Help", "Keys & Workflow", "")
    pane.mount(Markdown(
        "## Keys\n"
        "- `F1..F12` Tabs\n"
        "- `[` `]` Target\n"
        "- `/` Search focus\n"
        "- `Space` Toggle\n"
        "- `a` Selection → Plan\n"
        "- `q` QuickAdd\n"
        "- `i` Apply\n"
        "- `x` Export\n"
    , classes="infobox"))

async def on_button(app, bid: str) -> bool:
    return False

