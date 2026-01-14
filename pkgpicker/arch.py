from __future__ import annotations
import os
import shutil
import subprocess
import time
from typing import List, Set, Tuple

def which(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def run_capture(cmd: List[str]) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return p.returncode, p.stdout
    except FileNotFoundError:
        return 127, f"Command not found: {cmd[0]}"

def sh_quote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"

def pacman_installed_all() -> Set[str]:
    rc, out = run_capture(["pacman", "-Qq"])
    return set(out.split()) if rc == 0 else set()

def pacman_installed_explicit() -> List[str]:
    rc, out = run_capture(["pacman", "-Qqe"])
    xs = [x.strip() for x in out.splitlines() if x.strip()] if rc == 0 else []
    xs.sort()
    return xs

def pacman_repo_packages() -> Set[str]:
    rc, out = run_capture(["pacman", "-Qnq"])
    return set(out.split()) if rc == 0 else set()

def pacman_foreign_packages() -> Set[str]:
    rc, out = run_capture(["pacman", "-Qmq"])
    return set(out.split()) if rc == 0 else set()

def pacman_orphans() -> List[str]:
    rc, out = run_capture(["bash", "-lc", "pacman -Qtdq 2>/dev/null || true"])
    return [x for x in out.split() if x.strip()]

def systemctl_is_enabled(unit: str) -> str:
    rc, out = run_capture(["systemctl", "is-enabled", unit])
    s = out.strip()
    return s if s else ("not-found" if rc != 0 else "")

def systemctl_is_active(unit: str) -> str:
    rc, out = run_capture(["systemctl", "is-active", unit])
    s = out.strip()
    return s if s else ("not-found" if rc != 0 else "")

def paccache_clean() -> Tuple[int, str]:
    if not which("paccache"):
        return 127, "paccache not found (install pacman-contrib)."
    return run_capture(["sudo", "paccache", "-r"])

def lspci_full() -> str:
    if which("lspci"):
        rc, out = run_capture(["lspci", "-nnk"])
        return out if rc == 0 else ""
    return ""

def pacman_repo_has(pkg: str) -> bool:
    rc, _ = run_capture(["pacman", "-Si", pkg])
    return rc == 0

def aur_has_yay(pkg: str) -> bool:
    if not which("yay"):
        return False
    rc, _ = run_capture(["yay", "-Si", pkg])
    return rc == 0

def sudo_write_file(path: str, content: str) -> int:
    """
    Writes a file via sudo, with timestamped backup if existing.
    """
    ts = time.strftime("%Y%m%d-%H%M%S")
    script = (
        "set -e\n"
        f"if [ -f {sh_quote(path)} ]; then cp {sh_quote(path)} {sh_quote(path)}.bak-{ts}; fi\n"
        f"install -d -m 0755 {sh_quote(os.path.dirname(path) or '/')} \n"
        f"cat > {sh_quote(path)} <<'EOF'\n{content}\nEOF\n"
    )
    return subprocess.call(["sudo", "sh", "-lc", script])

def backup_write_user(path: str, content: str) -> str:
    """
    Writes user config with backup if existing.
    """
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        ts = time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, f"{path}.bak-{ts}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

