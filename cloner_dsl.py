#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple roles.dsl → permission overrides by role name."""

import os
import re
from typing import Dict, Optional

from app_paths import data_path

_PERM_ALIASES = {
    "administrator": "Administrator",
    "admin": "Administrator",
    "managechannels": "ManageChannels",
    "manage_roles": "ManageRoles",
    "manageroles": "ManageRoles",
    "kickmembers": "KickMembers",
    "banmembers": "BanMembers",
    "moderatemembers": "ModerateMembers",
}


def _parse_perm(name: str, perm_map: dict) -> Optional[int]:
    key = name.strip().replace(" ", "").replace("_", "").lower()
    if key in _PERM_ALIASES:
        name = _PERM_ALIASES[key]
    for k, v in perm_map.items():
        if k.lower() == name.lower() or k.replace("_", "").lower() == key:
            return v
    return None


def load_roles_dsl(path: Optional[str] = None, perm_map: Optional[dict] = None) -> Dict[str, dict]:
    p = path or data_path("roles.dsl")
    if not perm_map or not os.path.isfile(p):
        return {}
    text = open(p, encoding="utf-8").read()
    roles: Dict[str, dict] = {}
    blocks = re.findall(r'role\s+"([^"]+)"\s*\{([^}]*)\}', text, re.I | re.S)
    for name, body in blocks:
        allow = 0
        deny = 0
        hoist = False
        mentionable = False
        color = None
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith(";"):
                line = line[:-1].strip()
            low = line.lower()
            if low == "hoist":
                hoist = True
                continue
            if low == "mentionable":
                mentionable = True
                continue
            if low.startswith("color"):
                m = re.search(r"0x([0-9a-fA-F]+)", line)
                if m:
                    color = int(m.group(1), 16)
                continue
            m = re.match(r"(allow|deny)\s+(.+)", line, re.I)
            if not m:
                continue
            kind, rest = m.group(1).lower(), m.group(2)
            for part in re.split(r"[,+]", rest):
                bit = _parse_perm(part, perm_map)
                if bit is None:
                    continue
                if kind == "allow":
                    allow |= bit
                else:
                    deny |= bit
        roles[name] = {
            "permissions": str(allow & ~deny),
            "hoist": hoist,
            "mentionable": mentionable,
        }
        if color is not None:
            roles[name]["color"] = color
    return roles
