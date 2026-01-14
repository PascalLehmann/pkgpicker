from __future__ import annotations
import os, time, re
from typing import Any, Dict, List

def log_history(path: str, action: str, lines: List[str], rc: int) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {action} rc={rc}\n")
        for l in lines:
            f.write("  " + l + "\n")
        f.write("\n")

def parse_history(path: str, max_entries: int = 500) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    txt = open(path, "r", encoding="utf-8").read()
    blocks = [b.strip() for b in txt.split("\n\n") if b.strip()]
    entries: List[Dict[str, Any]] = []
    for b in blocks[-max_entries:]:
        lines = b.splitlines()
        m = re.match(r"^\[(.*?)\]\s+(\w+)\s+rc=(\d+)", lines[0].strip())
        if not m:
            continue
        ts, action, rc = m.group(1), m.group(2), int(m.group(3))
        cmds = [ln.strip() for ln in lines[1:] if ln.strip()]
        entries.append({"ts": ts, "action": action, "rc": rc, "cmds": cmds})
    entries.reverse()
    return entries

