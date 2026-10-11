"""Research metric definitions used by the final experiment runner."""

from __future__ import annotations
from typing import Mapping


def recovery_accuracy(rows):
    if not rows:
        return 0.0
    return sum(bool(r.get("action_correct", False)) for r in rows) / len(rows)


def governance_compliance(rows):
    if not rows:
        return 0.0
    return sum(bool(r.get("governance_compliance", False)) for r in rows) / len(rows)


def operational_reliability(rows):
    if not rows:
        return 0.0
    return sum(bool(r.get("operational_reliability", False)) for r in rows) / len(rows)


def self_healing_rate(rows):
    if not rows:
        return 0.0
    return sum(bool(r.get("self_healing_success", False)) for r in rows) / len(rows)


def mean_mttr(rows):
    vals = [float(r["mttr_sec"]) for r in rows if r.get("mttr_sec") is not None]
    return sum(vals) / len(vals) if vals else None
