from __future__ import annotations
import json, os, re, time
from typing import Any, Dict, List
from .arch import which, run_capture

def load_json_safe(path: str, default: Any) -> Any:
    try:
        if not os.path.exists(path):
            return default
        raw = open(path, "r", encoding="utf-8").read()
        if not raw.strip():
            return default
        return json.loads(raw)
    except Exception:
        return default

def save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def cached_search(cache_file: str, kind: str, query: str, ttl_sec: int = 1800) -> List[Dict[str, str]]:
    cache = load_json_safe(cache_file, {"ts": 0, "repo": {}, "aur": {}})
    if not isinstance(cache, dict):
        cache = {"ts": 0, "repo": {}, "aur": {}}
    now = int(time.time())
    if now - int(cache.get("ts", 0)) > ttl_sec:
        cache = {"ts": now, "repo": {}, "aur": {}}

    cache.setdefault(kind, {})
    if query in cache[kind]:
        return cache[kind][query]

    results: List[Dict[str, str]] = []
    if kind == "repo":
        rc, out = run_capture(["pacman", "-Ss", query])
        if rc == 0:
            lines = out.splitlines()
            for i in range(0, len(lines), 2):
                if i + 1 >= len(lines):
                    break
                head = lines[i].strip()
                desc = lines[i + 1].strip()
                m = re.match(r"^\S+/(\S+)\s", head)
                if m:
                    results.append({"name": m.group(1), "desc": desc})
    else:
        if which("yay"):
            rc, out = run_capture(["yay", "-Ss", query])
            if rc == 0:
                for ln in out.splitlines():
                    ln = ln.strip()
                    m = re.match(r"^(?:aur/)?([a-zA-Z0-9@._+-]+)\s", ln)
                    if m:
                        results.append({"name": m.group(1), "desc": ln})

    cache[kind][query] = results[:500]
    cache["ts"] = now
    save_json(cache_file, cache)
    return results[:500]

def pkginfo_installed(pkginfo_cache_file: str, pkg: str) -> Dict[str, str]:
    cache = load_json_safe(pkginfo_cache_file, {})
    if isinstance(cache, dict) and pkg in cache:
        return cache[pkg]

    info = {"name": pkg, "ver": "", "repo": "", "desc": ""}

    if which("expac"):
        rc, out = run_capture(["expac", "-Q", "%n\t%v\t%r\t%d", pkg])
        if rc == 0 and out.strip():
            parts = out.strip().split("\t", 3)
            if len(parts) > 1: info["ver"] = parts[1]
            if len(parts) > 2: info["repo"] = parts[2]
            if len(parts) > 3: info["desc"] = parts[3]

    if not info["desc"] or not info["ver"]:
        rc, out = run_capture(["pacman", "-Qi", pkg])
        if rc == 0:
            for ln in out.splitlines():
                if ln.startswith("Version"): info["ver"] = ln.split(":", 1)[1].strip()
                elif ln.startswith("Repository"): info["repo"] = ln.split(":", 1)[1].strip()
                elif ln.startswith("Description"): info["desc"] = ln.split(":", 1)[1].strip()

    if not isinstance(cache, dict):
        cache = {}
    cache[pkg] = info
    save_json(pkginfo_cache_file, cache)
    return info

