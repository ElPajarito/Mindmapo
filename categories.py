"""Pentest-oriented categories and visual theme for the mind map.

Each category is a lively, saturated "power-up" color so the canvas feels like a
Mario world full of blocks rather than a boring diagram.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    emoji: str
    color: str  # base hex color


# Ordered so the most "early kill-chain" stuff is at the top of the palette.
CATEGORIES = {
    "target":  Category("target",  "Target",        "\U0001F3AF", "#FF4D4D"),
    "recon":   Category("recon",    "Recon",         "\U0001F50D", "#4D96FF"),
    "scan":    Category("scan",     "Scanning",      "\U0001F4E1", "#38BDF8"),
    "enum":    Category("enum",     "Enumeration",   "\U0001F4CB", "#2DD4BF"),
    "vuln":    Category("vuln",     "Vulnerability", "\U0001F41E", "#FB923C"),
    "exploit": Category("exploit",  "Exploitation",  "\U0001F4A5", "#F43F5E"),
    "creds":   Category("creds",    "Credentials",   "\U0001F511", "#FACC15"),
    "privesc": Category("privesc",  "Priv Esc",      "⬆️", "#A78BFA"),
    "lateral": Category("lateral",  "Lateral Move",  "↔️", "#34D399"),
    "persist": Category("persist",  "Persistence",   "\U0001F4CC", "#F59E0B"),
    "exfil":   Category("exfil",    "Exfiltration",  "\U0001F4E4", "#F472B6"),
    "note":    Category("note",     "Note",          "\U0001F4DD", "#94A3B8"),
}

DEFAULT_CATEGORY = "note"


def get_category(key: str) -> Category:
    return CATEGORIES.get(key, CATEGORIES[DEFAULT_CATEGORY])


# ---- Global dark "night-world" palette -------------------------------------
THEME = {
    "bg_top":     "#0e1326",
    "bg_bottom":  "#161d3a",
    "grid_dot":   "#243056",
    "panel":      "#121829",
    "panel_alt":  "#1a2238",
    "text":       "#e8edf7",
    "text_dim":   "#8a97b8",
    "accent":     "#FFCC00",  # coin gold
    "border":     "#2a3656",
}
