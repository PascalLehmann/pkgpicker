from __future__ import annotations

import re
from typing import List, Tuple

from textual.containers import Horizontal
from textual.widgets import Button, Static

from ..arch import lspci_full

def build(app, pane):
    app.mount_topcard(pane, "ReadyCheck", "Hardware scan → Driver suggestions (Wayland-first) + Add to Plan", "Button: add suggested drivers to plan")
    pane.mount(
        Horizontal(
            Button("Scan hardware", id="btn_ready_scan", variant="primary"),
            Button("Add suggested drivers → Plan", id="btn_ready_add", variant="success"),
            classes="toolbar",
        )
    )
    pane.mount(Static("", id="ready_out", classes="infobox"))
    _render(app, scan=False)

def _detect_gpu_pkgs(lspci_txt: str) -> Tuple[str, List[str]]:
    t = lspci_txt.lower()
    # rough heuristics
    if "nvidia" in t:
        return "NVIDIA", ["nvidia", "nvidia-utils", "lib32-nvidia-utils", "vulkan-icd-loader", "lib32-vulkan-icd-loader"]
    if "advanced micro devices" in t or "amd/ati" in t or "radeon" in t:
        return "AMD", ["mesa", "vulkan-radeon", "lib32-mesa", "lib32-vulkan-radeon", "vulkan-icd-loader", "lib32-vulkan-icd-loader"]
    if "intel" in t:
        return "Intel", ["mesa", "vulkan-intel", "lib32-mesa", "lib32-vulkan-intel", "vulkan-icd-loader", "lib32-vulkan-icd-loader"]
    return "Unknown", ["mesa", "vulkan-icd-loader"]

def _suggest_base_wayland() -> List[str]:
    return [
        "pipewire", "wireplumber", "pipewire-pulse",
        "xdg-desktop-portal", "xdg-desktop-portal-wlr",
        "qt6-wayland", "qt5-wayland",
    ]

def _render(app, scan: bool):
    box = app.query_one("#ready_out", Static)
    txt = lspci_full() if scan else ""
    if not txt:
        box.update("Hardware scan not run yet.\n\nClick [b]Scan hardware[/b].")
        app._ready_cache = {"vendor": "?", "pkgs": []}  # type: ignore[attr-defined]
        return

    vendor, gpu_pkgs = _detect_gpu_pkgs(txt)
    base = _suggest_base_wayland()
    pkgs = base + gpu_pkgs

    missing = [p for p in pkgs if p not in app.installed_all]
    body = [
        f"[b]GPU vendor[/b]: {vendor}",
        "",
        "[b]Suggested packages[/b]:",
        "  " + " ".join(pkgs),
        "",
        f"[b]Missing[/b] ({len(missing)}):",
        "  " + " ".join(missing),
        "",
        "[b]lspci -nnk[/b] (truncated):",
        txt[:3500],
    ]
    box.update("\n".join(body))
    app._ready_cache = {"vendor": vendor, "pkgs": pkgs, "missing": missing}  # type: ignore[attr-defined]

async def on_button(app, bid: str) -> bool:
    if bid == "btn_ready_scan":
        _render(app, scan=True)
        app.set_last("ReadyCheck scanned")
        return True
    if bid == "btn_ready_add":
        cache = getattr(app, "_ready_cache", {}) or {}
        pkgs = list(cache.get("missing", []) or [])
        for p in pkgs:
            app.plan_repo.add(p)
        app.set_last(f"Added {len(pkgs)} driver/base pkgs to plan")
        try:
            from . import plan_tab
            plan_tab.refresh(app)
        except Exception:
            pass
        return True
    return False

