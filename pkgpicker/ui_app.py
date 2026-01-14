from __future__ import annotations

import asyncio
import os
import threading
from typing import Any, Dict, List, Optional, Set

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TabbedContent, TabPane, DataTable

from .models import Category, Target, ConflictRule, PackageItem
from .arch import (
    pacman_installed_all,
    pacman_installed_explicit,
    pacman_repo_packages,
    pacman_foreign_packages,
)
from .cache import load_json_safe
from .history import parse_history
from .modals import ConfirmModal, OutputModal

from .tabs import (
    packages_tab,
    search_tab,
    plan_tab,
    installed_tab,
    ready_tab,
    services_tab,
    presets_tab,
    hygiene_tab,
    history_tab,
    selfcheck_tab,
    help_tab,
)

APP_NAME = "pkgpicker"

def mkdirp(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def conflict_problems(selected: Set[str], rules: List[ConflictRule]) -> List[str]:
    probs: List[str] = []
    for r in rules:
        present = [p for p in r.group if p in selected]
        if r.mode == "exactly_one":
            if len(present) != 1:
                probs.append(f"{r.name}: erwartet genau 1, aktuell: {present if present else 'none'}")
        else:
            if len(present) > 1:
                probs.append(f"{r.name}: zu viele ausgewählt: {present}")
    return probs

def parse_categories(cfg: Dict[str, Any]) -> List[Category]:
    out: List[Category] = []
    for c in cfg.get("categories", []) or []:
        items: List[PackageItem] = []
        for it in c.get("items", []) or []:
            if isinstance(it, str):
                nm = it.strip()
                if nm:
                    items.append(PackageItem(name=nm, source="repo"))
            elif isinstance(it, dict):
                nm = str(it.get("name", "")).strip()
                if not nm:
                    continue
                items.append(
                    PackageItem(
                        name=nm,
                        source=str(it.get("source", "repo")).strip(),
                        desc=str(it.get("desc", "")).strip(),
                        featured=bool(it.get("featured", False)),
                        reason=str(it.get("reason", "")).strip(),
                    )
                )
        out.append(Category(name=str(c.get("name", "")).strip(), items=items))
    return out

def parse_targets(cfg: Dict[str, Any]) -> List[Target]:
    out: List[Target] = []
    for t in cfg.get("targets", []) or []:
        out.append(
            Target(
                id=str(t.get("id", "")).strip(),
                name=str(t.get("name", "")).strip(),
                required_packages=list(t.get("required_packages", []) or []),
                recommended_packages=list(t.get("recommended_packages", []) or []),
                services=list(t.get("services", []) or []),
                preset=str(t.get("preset", "hyprland")).strip(),
            )
        )
    return out

def parse_conflicts(cfg: Dict[str, Any]) -> List[ConflictRule]:
    out: List[ConflictRule] = []
    for r in cfg.get("conflicts", []) or []:
        out.append(
            ConflictRule(
                name=str(r.get("name", "conflict")),
                group=list(r.get("group", []) or []),
                mode=str(r.get("mode", "at_most_one")),
            )
        )
    return out

class PkgPickerApp(App):
    CACHE_DIR = os.path.join(os.path.expanduser("~/.cache/pkgpicker"))
    HISTORY_LOG = os.path.join(CACHE_DIR, "history.log")
    SEARCH_CACHE_FILE = os.path.join(CACHE_DIR, "search_cache.json")
    PKGINFO_CACHE_FILE = os.path.join(CACHE_DIR, "pkginfo_cache.json")
    PROFILES_DIR = os.path.join(CACHE_DIR, "profiles")
    EXPORTS_DIR = os.path.join(CACHE_DIR, "exports")
    BUNDLES_DIR = os.path.join(EXPORTS_DIR, "bundles")

    CSS = """
    Screen { background: $background; }
    Header { background: $panel; }
    Footer { background: $panel; }

    #inst_row { height: 1fr; }
    #inst_tbl { width: 4fr; height: 1fr; }
    #inst_right { width: 2fr; min-width: 40; height: 1fr; }
    #inst_info { height: 1fr; overflow: auto; }

    #statusbar { height: auto; border: round $primary; background: $boost; padding: 0 2; margin: 0 1 1 1; }
    #busy { height: 1; color: $warning; padding: 0 2; margin: 0 1 1 1; }

    .topcard { height: auto; border: round $primary; background: $panel; padding: 1 2; margin: 0 1 1 1; }
    .infobox { border: round $primary; background: $boost; padding: 1 2; margin: 0 1 1 1; }
    .toolbar { height: auto; padding: 0 1; margin: 0 1 1 1; }
    .toolbar Button { margin: 0 1 0 0; }

    DataTable { height: 1fr; border: round $surface; background: $panel; margin: 0 1 1 1; }
    Input { border: round $surface; background: $panel; margin: 0 1 1 1; }

    #modal { width: 92%; max-width: 170; padding: 1 2; border: round $primary; background: $panel; }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Beenden"),
        ("f1", "go_help", "Help"),
        ("f2", "go_selfcheck", "Self-Check"),
        ("f3", "go_packages", "Packages"),
        ("f4", "go_search", "Search"),
        ("f5", "go_installed", "Installed"),
        ("f6", "go_plan", "Plan"),
        ("f8", "go_ready", "Ready"),
        ("f9", "go_services", "Services"),
        ("f10", "go_presets", "Presets"),
        ("f11", "go_hygiene", "Hygiene"),
        ("f12", "go_history", "History"),
        ("r", "refresh", "Refresh"),
        ("[", "target_prev", "Target prev"),
        ("]", "target_next", "Target next"),
        ("/", "focus_search", "Focus Search"),
        ("space", "toggle", "Toggle"),
        ("enter", "info", "Info"),
        ("a", "add_plan", "Selection→Plan"),
        ("q", "quick_add", "Quick Add"),
        ("i", "apply_plan", "Apply Plan"),
        ("x", "export_csv", "Export CSV"),
        ("p", "profile_save", "Profile Save"),
        ("l", "profile_load", "Profile Load"),
    ]

    def __init__(self, data_path: str):
        super().__init__()
        self.data_path = data_path
        self.cfg = self._load_config(data_path)

        self.categories = parse_categories(self.cfg)
        self.targets = parse_targets(self.cfg)
        self.conflicts = parse_conflicts(self.cfg)

        self.target_idx = 0
        self.cat_idx = 0

        # installed state
        self.installed_all: Set[str] = set()
        self.installed_explicit: List[str] = []
        self.installed_repo: Set[str] = set()
        self.installed_foreign: Set[str] = set()
        self.history: List[Dict[str, Any]] = []

        # selection + plan
        self.selected_repo: Set[str] = set()
        self.selected_aur: Set[str] = set()
        self.plan_repo: Set[str] = set()
        self.plan_aur: Set[str] = set()
        self.remove_explicit: Set[str] = set()

        # services plan
        self.plan_services_enable: Set[str] = set()
        self.plan_services_disable: Set[str] = set()

        # preset/config generation
        self.plan_preset: Optional[str] = None
        self.plan_generate_configs: bool = False

        self.last_action = "Ready."
        self.busy = ""

    # ---------- modal helpers ----------
    async def push_result(self, screen) -> Any:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[Any] = loop.create_future()

        def _cb(result: Any) -> None:
            if not fut.done():
                fut.set_result(result)

        self.push_screen(screen, callback=_cb)
        return await fut

    async def ask_confirm(self, title: str, body: str) -> bool:
        return bool(await self.push_result(ConfirmModal(title, body)))

    def show_output(self, title: str, body: str) -> None:
        self.push_screen(OutputModal(title, body))

    def _load_config(self, path: str) -> Dict[str, Any]:
        default_cfg = {
            "ui": {"title": "PkgPicker", "tagline": "Minimal → Wayland Desktop + Packages + Services"},
            "categories": [],
            "targets": [],
            "conflicts": [],
            "services": [],
            "presets": [],
        }
        cfg = load_json_safe(path, default_cfg)
        if not isinstance(cfg, dict):
            cfg = default_cfg
        for k, v in default_cfg.items():
            cfg.setdefault(k, v)
        return cfg

    # ---------- basics ----------
    def current_target(self) -> Target:
        if not self.targets:
            return Target("none", "(keine targets in packages.json)", [], [], [], "hyprland")
        return self.targets[self.target_idx]

    def refresh_all(self) -> None:
        self.installed_all = pacman_installed_all()
        self.installed_explicit = pacman_installed_explicit()
        self.installed_repo = pacman_repo_packages()
        self.installed_foreign = pacman_foreign_packages()
        self.history = parse_history(self.HISTORY_LOG)

    def set_busy(self, msg: str) -> None:
        self.busy = msg
        try:
            self.query_one("#busy", Static).update(msg)
        except Exception:
            pass

    def set_last(self, msg: str) -> None:
        self.last_action = msg
        self.update_status()

    def update_status(self) -> None:
        t = self.current_target()
        combined = set(self.installed_all) | self.plan_repo | self.plan_aur | self.selected_repo | self.selected_aur
        probs = conflict_problems(combined, self.conflicts)
        s = (
            f"Target: {t.name}   "
            f"Sel: repo={len(self.selected_repo)} aur={len(self.selected_aur)}   "
            f"Plan: +repo={len(self.plan_repo)} +aur={len(self.plan_aur)}  -rm={len(self.remove_explicit)}   "
            f"SvcPlan: +{len(self.plan_services_enable)} -{len(self.plan_services_disable)}   "
            f"Conflicts: {len(probs)}   "
            f"Last: {self.last_action}"
        )
        try:
            self.query_one("#statusbar", Static).update(s)
        except Exception:
            pass

    def mount_topcard(self, pane: TabPane, title: str, subtitle: str = "", keys: str = "") -> None:
        lines = [f"[b]{title}[/b]"]
        if subtitle:
            lines.append(f"[dim]{subtitle}[/dim]")
        if keys:
            lines.append(f"[dim]{keys}[/dim]")
        pane.mount(Static("\n".join(lines), classes="topcard"))

    @staticmethod
    def safe_cursor_row(tbl: DataTable) -> None:
        try:
            tbl.cursor_type = "row"  # type: ignore[attr-defined]
        except Exception:
            pass

    # ---------- statusbar visibility fix (Self-Check/Help) ----------
    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        pane_id = getattr(event.pane, "id", "") or ""
        hide = pane_id in ("tab_selfcheck", "tab_help")
        try:
            self.query_one("#statusbar", Static).styles.display = "none" if hide else "block"
            self.query_one("#busy", Static).styles.display = "none" if hide else "block"
        except Exception:
            pass

    # ---------- app layout ----------
    def compose(self) -> ComposeResult:
        ui = self.cfg.get("ui", {}) or {}
        yield Header(show_clock=True, name=str(ui.get("title", "PkgPicker")))
        yield Static("", id="statusbar")
        yield Static("", id="busy")
        with TabbedContent(id="tabs"):
            yield TabPane("Packages", id="tab_packages")
            yield TabPane("Search", id="tab_search")
            yield TabPane("Plan", id="tab_plan")
            yield TabPane("Installed", id="tab_installed")
            yield TabPane("ReadyCheck", id="tab_ready")
            yield TabPane("Services", id="tab_services")
            yield TabPane("Presets", id="tab_presets")
            yield TabPane("Hygiene", id="tab_hygiene")
            yield TabPane("History", id="tab_history")
            yield TabPane("Self-Check", id="tab_selfcheck")
            yield TabPane("Help", id="tab_help")
        yield Footer()

    def on_mount(self) -> None:
        mkdirp(self.CACHE_DIR)
        mkdirp(self.PROFILES_DIR)
        mkdirp(self.EXPORTS_DIR)
        mkdirp(self.BUNDLES_DIR)

        self.refresh_all()
        self.build_all()

        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "tab_packages"

        self.update_status()
        # enforce initial visibility
        hide = (tabs.active or "") in ("tab_selfcheck", "tab_help")
        self.query_one("#statusbar", Static).styles.display = "none" if hide else "block"
        self.query_one("#busy", Static).styles.display = "none" if hide else "block"

    def clear_pane(self, pane_id: str) -> TabPane:
        pane = self.query_one(f"#{pane_id}", TabPane)
        pane.remove_children()
        return pane

    def build_all(self) -> None:
        packages_tab.build(self, self.clear_pane("tab_packages"))
        search_tab.build(self, self.clear_pane("tab_search"))
        plan_tab.build(self, self.clear_pane("tab_plan"))
        installed_tab.build(self, self.clear_pane("tab_installed"))
        ready_tab.build(self, self.clear_pane("tab_ready"))
        services_tab.build(self, self.clear_pane("tab_services"))
        presets_tab.build(self, self.clear_pane("tab_presets"))
        hygiene_tab.build(self, self.clear_pane("tab_hygiene"))
        history_tab.build(self, self.clear_pane("tab_history"))
        selfcheck_tab.build(self, self.clear_pane("tab_selfcheck"))
        help_tab.build(self, self.clear_pane("tab_help"))

    # ---------- navigation actions ----------
    def _go(self, tab_id: str) -> None:
        self.query_one("#tabs", TabbedContent).active = tab_id

    def action_go_help(self) -> None: self._go("tab_help")
    def action_go_selfcheck(self) -> None: self._go("tab_selfcheck")
    def action_go_packages(self) -> None: self._go("tab_packages")
    def action_go_search(self) -> None: self._go("tab_search")
    def action_go_installed(self) -> None: self._go("tab_installed")
    def action_go_plan(self) -> None: self._go("tab_plan")
    def action_go_ready(self) -> None: self._go("tab_ready")
    def action_go_services(self) -> None: self._go("tab_services")
    def action_go_presets(self) -> None: self._go("tab_presets")
    def action_go_hygiene(self) -> None: self._go("tab_hygiene")
    def action_go_history(self) -> None: self._go("tab_history")

    def action_focus_search(self) -> None:
        self._go("tab_search")
        search_tab.focus_input(self)

    def action_refresh(self) -> None:
        self.refresh_all()
        self.build_all()
        self.set_last("Refreshed.")

    def action_target_prev(self) -> None:
        if not self.targets:
            return
        self.target_idx = max(0, self.target_idx - 1)
        self.refresh_all()
        packages_tab.refresh(self)
        self.set_last("Target geändert.")

    def action_target_next(self) -> None:
        if not self.targets:
            return
        self.target_idx = min(len(self.targets) - 1, self.target_idx + 1)
        self.refresh_all()
        packages_tab.refresh(self)
        self.set_last("Target geändert.")

    # ---------- global dispatch ----------
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        table_id = getattr(event.data_table, "id", "")
        if packages_tab.on_row_highlighted(self, event, table_id): return
        if search_tab.on_row_highlighted(self, event, table_id): return
        if installed_tab.on_row_highlighted(self, event, table_id): return
        if services_tab.on_row_highlighted(self, event, table_id): return
        if history_tab.on_row_highlighted(self, event, table_id): return
        if plan_tab.on_row_highlighted(self, event, table_id): return

    async def on_button_pressed(self, event) -> None:
        bid = event.button.id
        if await packages_tab.on_button(self, bid): return
        if await search_tab.on_button(self, bid): return
        if await plan_tab.on_button(self, bid): return
        if await installed_tab.on_button(self, bid): return
        if await ready_tab.on_button(self, bid): return
        if await services_tab.on_button(self, bid): return
        if await presets_tab.on_button(self, bid): return
        if await hygiene_tab.on_button(self, bid): return
        if await history_tab.on_button(self, bid): return
        if await selfcheck_tab.on_button(self, bid): return
        if await help_tab.on_button(self, bid): return

    # ---------- key actions ----------
    def action_toggle(self) -> None:
        if packages_tab.action_toggle(self): return
        if search_tab.action_toggle(self): return
        if installed_tab.action_toggle(self): return
        if services_tab.action_toggle(self): return
        if plan_tab.action_toggle(self): return

    def action_info(self) -> None:
        if packages_tab.action_info(self): return
        if search_tab.action_info(self): return
        if installed_tab.action_info(self): return
        if services_tab.action_info(self): return
        if plan_tab.action_info(self): return

    def action_add_plan(self) -> None:
        plan_tab.add_selection_to_plan(self)

    async def action_quick_add(self) -> None:
        await plan_tab.quick_add(self)

    async def action_apply_plan(self) -> None:
        await plan_tab.apply_plan(self)

    async def action_export_csv(self) -> None:
        await installed_tab.export_csv(self)

    async def action_profile_save(self) -> None:
        await plan_tab.profile_save(self)

    async def action_profile_load(self) -> None:
        await plan_tab.profile_load(self)

