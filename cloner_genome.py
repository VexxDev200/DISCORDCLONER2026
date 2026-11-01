#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalized server structure fingerprint and diff."""

import hashlib
import json
from typing import Any, Dict, List, Tuple


def _norm_role(r: dict) -> dict:
    return {
        "name": r.get("name"),
        "color": int(r.get("color") or 0),
        "hoist": bool(r.get("hoist")),
        "mentionable": bool(r.get("mentionable")),
        "permissions": str(r.get("permissions", "0")),
        "position": int(r.get("position") or 0),
    }


def _norm_channel(c: dict) -> dict:
    ow = []
    for x in c.get("permission_overwrites") or []:
        ow.append(
            {
                "type": x.get("type"),
                "allow": str(x.get("allow", "0")),
                "deny": str(x.get("deny", "0")),
            }
        )
    return {
        "name": c.get("name"),
        "type": c.get("type"),
        "position": int(c.get("position") or 0),
        "parent": c.get("parent_id"),
        "topic": (c.get("topic") or "")[:500],
        "nsfw": bool(c.get("nsfw")),
        "overwrites": sorted(ow, key=lambda z: (z.get("type"), z.get("allow"), z.get("deny"))),
    }


def build_genome(guild_id: str, roles: List[dict], channels: List[dict], emojis: List[dict]) -> dict:
    roles_n = sorted(
        [_norm_role(r) for r in roles if r.get("name") != "@everyone" and not r.get("managed")],
        key=lambda x: x["name"] or "",
    )
    ch_n = sorted([_norm_channel(c) for c in channels], key=lambda x: (x.get("type"), x.get("name") or ""))
    em_n = sorted([{"name": e.get("name")} for e in emojis], key=lambda x: x["name"] or "")
    return {
        "guild_id": str(guild_id),
        "roles": roles_n,
        "channels": ch_n,
        "emojis": em_n,
    }


def build_genome_from_snapshot_payload(payload: dict) -> dict:
    if not payload:
        return {}
    gid = (payload.get("guild") or {}).get("id") or payload.get("guild_id") or ""
    return build_genome(
        gid,
        payload.get("roles") or [],
        payload.get("channels") or [],
        payload.get("emojis") or [],
    )


def genome_digest(genome: dict) -> str:
    raw = json.dumps(genome, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compare_genomes(source: dict, target: dict) -> Tuple[float, List[str]]:
    if not source or not target:
        return 0.0, ["empty genome"]
    notes: List[str] = []
    score_parts: List[float] = []

    def _set_score(label: str, a_list: list, b_list: list, key_fn):
        a_map = {key_fn(x): x for x in a_list}
        b_map = {key_fn(x): x for x in b_list}
        keys = set(a_map) | set(b_map)
        if not keys:
            score_parts.append(100.0)
            return
        ok = 0
        for k in keys:
            if k in a_map and k in b_map and a_map[k] == b_map[k]:
                ok += 1
            elif k in a_map and k not in b_map:
                notes.append(f"missing on target: {label} {k}")
            elif k in b_map and k not in a_map:
                notes.append(f"extra on target: {label} {k}")
            else:
                notes.append(f"diff: {label} {k}")
        score_parts.append(100.0 * ok / len(keys))

    _set_score("role", source.get("roles") or [], target.get("roles") or [], lambda x: x.get("name"))
    _set_score(
        "channel",
        source.get("channels") or [],
        target.get("channels") or [],
        lambda x: (x.get("type"), x.get("name")),
    )
    _set_score("emoji", source.get("emojis") or [], target.get("emojis") or [], lambda x: x.get("name"))
    pct = sum(score_parts) / max(len(score_parts), 1)
    return round(pct, 2), notes[:30]
