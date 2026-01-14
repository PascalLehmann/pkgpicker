from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List

@dataclass(frozen=True)
class PackageItem:
    name: str
    source: str  # repo|aur
    desc: str = ""
    featured: bool = False
    reason: str = ""

@dataclass(frozen=True)
class Category:
    name: str
    items: List[PackageItem]

@dataclass(frozen=True)
class Target:
    id: str
    name: str
    required_packages: List[str]
    recommended_packages: List[str]
    services: List[Any]  # str or dict
    preset: str  # hyprland|plasma

@dataclass(frozen=True)
class ConflictRule:
    name: str
    group: List[str]
    mode: str  # at_most_one | exactly_one

