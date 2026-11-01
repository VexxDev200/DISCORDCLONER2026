#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> str:
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(filename: str) -> str:
    if is_frozen():
        base = getattr(sys, "_MEIPASS", app_dir())
        return os.path.join(base, filename)
    return os.path.join(app_dir(), filename)


def data_path(filename: str) -> str:
    return os.path.join(app_dir(), filename)
