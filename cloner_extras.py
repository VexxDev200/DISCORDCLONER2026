#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chimera, Shadow, Time machine, Triad config, Entropy seal."""

import hashlib
import hmac
import json
from typing import Any, Dict

import cloner_genome


def entropy_seal(genome_hash: str, user_id: str, session_id: int) -> str:
    raw = f"{genome_hash}|{user_id}|{session_id}".encode("utf-8")
    digest = hmac.new(b"GodCloner-VEXX", raw, hashlib.sha256).hexdigest()[:8].upper()
    return f"VEXX-{digest}"


def apply_triad(strategy: str, config: Dict[str, Any]) -> Dict[str, Any]:
    s = strategy or "2"
    base = dict(config)
    if s == "1":
        base["genome_delta_only"] = True
        base["copy_stickers"] = False
        base["copy_scheduled_events"] = False
    elif s == "3":
        base["copy_emojis"] = False
        base["copy_stickers"] = False
        base["copy_webhooks"] = False
        base["copy_banner"] = False
        base["copy_icon"] = False
        base["copy_onboarding"] = False
        base["copy_automod"] = False
        base["copy_scheduled_events"] = False
        base["copy_members"] = False
    else:
        base["role_icons_on_boost_only"] = True
        base["keep_role_colors"] = True
    return base


def chimera_role_name(name: str, source_tag: str) -> str:
    tag = source_tag[:8]
    if name.startswith(f"[{tag}]"):
        return name[:100]
    return f"[{tag}] {name}"[:100]


def shadow_plan(source_genome: dict, target_genome: dict) -> dict:
    _, notes = cloner_genome.compare_genomes(source_genome, target_genome)
    return {"notes": notes, "source_hash": cloner_genome.genome_digest(source_genome)}
