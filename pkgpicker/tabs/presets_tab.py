from __future__ import annotations

from textual.containers import Horizontal
from textual.widgets import Button, Static

def build(app, pane):
    app.mount_topcard(
        pane,
        "Presets",
        "Greetd + tuigreet presets (Hyprland recommended, Plasma Wayland alternative)",
        "These presets add packages + services + config generation flags. Apply in Plan.",
    )

    pane.mount(
        Horizontal(
            Button("Preset: Hyprland + tuigreet", id="btn_preset_hypr", variant="success"),
            Button("Preset: Plasma Wayland + tuigreet", id="btn_preset_plasma", variant="primary"),
            Button("Toggle: generate configs", id="btn_preset_toggle_cfg", variant="warning"),
            classes="toolbar",
        )
    )
    pane.mount(Static("", id="preset_info", classes="infobox"))
    refresh(app)

def refresh(app):
    box = app.query_one("#preset_info", Static)
    body = (
        f"[b]Preset planned[/b]: {app.plan_preset or '-'}\n"
        f"[b]Generate configs[/b]: {'YES' if app.plan_generate_configs else 'no'}\n\n"
        "Hyprland preset adds typical Wayland stack (kitty/waybar/wofi/mako/hyprpaper/cliphist/grim/slurp etc.)\n"
        "Plasma preset adds startplasma-wayland + greetd/tuigreet.\n\n"
        "Apply is executed in [b]Plan[/b] tab."
    )
    box.update(body)

def _apply_common(app):
    # greetd + tuigreet + essentials
    for p in ["greetd", "tuigreet"]:
        app.plan_repo.add(p)
    app.plan_services_enable.add("greetd.service")

def _preset_hypr(app):
    _apply_common(app)
    # Hyprland stack
    pkgs = [
        "hyprland", "xorg-xwayland",
        "kitty", "waybar", "wofi", "mako", "hyprpaper",
        "wl-clipboard", "cliphist",
        "grim", "slurp",
        "pipewire", "wireplumber", "pipewire-pulse",
        "xdg-desktop-portal", "xdg-desktop-portal-wlr",
        "qt6-wayland", "qt5-wayland",
    ]
    for p in pkgs:
        app.plan_repo.add(p)
    app.plan_preset = "hyprland-tuigreet"

def _preset_plasma(app):
    _apply_common(app)
    pkgs = [
        "plasma-meta", "konsole",
        "xdg-desktop-portal", "xdg-desktop-portal-kde",
        "qt6-wayland", "qt5-wayland",
        "pipewire", "wireplumber", "pipewire-pulse",
    ]
    for p in pkgs:
        app.plan_repo.add(p)
    app.plan_preset = "plasma-tuigreet"

async def on_button(app, bid: str) -> bool:
    if bid == "btn_preset_hypr":
        _preset_hypr(app)
        app.plan_generate_configs = True
        app.set_last("Preset planned: hyprland-tuigreet")
        refresh(app)
        return True
    if bid == "btn_preset_plasma":
        _preset_plasma(app)
        app.plan_generate_configs = True
        app.set_last("Preset planned: plasma-tuigreet")
        refresh(app)
        return True
    if bid == "btn_preset_toggle_cfg":
        app.plan_generate_configs = not app.plan_generate_configs
        app.set_last("Toggled config generation")
        refresh(app)
        return True
    return False

