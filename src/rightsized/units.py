"""Kubernetes quantity parsing and formatting.

CPU is held as float cores, memory as int bytes, everywhere inside the tool.
"""

from __future__ import annotations

import math

_BIN = {"Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40}
_DEC = {"k": 10**3, "M": 10**6, "G": 10**9, "T": 10**12}

MI = 2**20


def parse_cpu(q: str | int | float | None) -> float | None:
    if q is None:
        return None
    if isinstance(q, (int, float)):
        return float(q)
    q = str(q).strip()
    if q.endswith("m"):
        return float(q[:-1]) / 1000
    return float(q)


def parse_memory(q: str | int | float | None) -> int | None:
    if q is None:
        return None
    if isinstance(q, (int, float)):
        return int(q)
    q = str(q).strip()
    for suffix, mult in _BIN.items():
        if q.endswith(suffix):
            return int(float(q[: -len(suffix)]) * mult)
    for suffix, mult in _DEC.items():
        if q.endswith(suffix):
            return int(float(q[: -len(suffix)]) * mult)
    return int(float(q))


def round_up(value: float, step: float) -> float:
    return math.ceil(value / step - 1e-9) * step


def format_cpu(cores: float) -> str:
    milli = int(round(cores * 1000))
    if milli % 1000 == 0:
        return str(milli // 1000)
    return f"{milli}m"


def format_memory(b: int) -> str:
    if b % _BIN["Gi"] == 0:
        return f"{b // _BIN['Gi']}Gi"
    return f"{math.ceil(b / MI)}Mi"
