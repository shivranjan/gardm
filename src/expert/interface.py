
"""Synthetic expert elicitation interface for development/calibration only."""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Mapping
import statistics


@dataclass(frozen=True)
class ExpertResponse:
    expert_id: str
    question_id: str
    parameter: str
    value: float
    confidence: float
    rationale: str
    provider: str = "synthetic"
    development_only: bool = True

    def to_dict(self):
        return asdict(self)


PARAMETERS = ("w_P", "w_R", "w_S", "w_H", "w_F")


def synthetic_weight_responses(
    expert_ids: List[str] | None = None,
) -> List[ExpertResponse]:
    """Generate deterministic synthetic responses around provisional weights.

    These responses are placeholders for interface/schema testing only.
    They must not be represented as real expert evidence.
    """
    expert_ids = expert_ids or ["SYN-E01", "SYN-E02", "SYN-E03", "SYN-E04", "SYN-E05"]
    base = {"w_P": .20, "w_R": .25, "w_S": .20, "w_H": .15, "w_F": .20}
    offsets = [
        {"w_P": .01, "w_R": 0,    "w_S": -.01, "w_H": 0,    "w_F": 0},
        {"w_P": 0,    "w_R": .01, "w_S": 0,    "w_H": -.01, "w_F": 0},
        {"w_P": -.01,"w_R": 0,    "w_S": .01, "w_H": 0,    "w_F": 0},
        {"w_P": 0,    "w_R": -.01,"w_S": 0,    "w_H": .01, "w_F": 0},
        {"w_P": 0,    "w_R": 0,    "w_S": 0,    "w_H": 0,    "w_F": 0},
    ]
    rows = []
    for eid, offset in zip(expert_ids, offsets):
        for p in PARAMETERS:
            rows.append(ExpertResponse(
                expert_id=eid,
                question_id=f"WEIGHT-{p}",
                parameter=p,
                value=round(base[p] + offset[p], 4),
                confidence=.80,
                rationale="Synthetic development response for interface validation.",
            ))
    return rows


def aggregate_weights(responses: List[ExpertResponse]) -> Dict[str, float]:
    """Aggregate expert weights by arithmetic mean, then normalize."""
    if not responses:
        raise ValueError("No expert responses supplied.")
    grouped = {p: [] for p in PARAMETERS}
    for r in responses:
        if r.parameter not in grouped:
            raise ValueError(f"Unknown parameter: {r.parameter}")
        if not (0 <= r.value <= 1):
            raise ValueError("Expert weight values must be in [0,1].")
        if not (0 <= r.confidence <= 1):
            raise ValueError("Confidence must be in [0,1].")
        grouped[r.parameter].append(r.value)

    means = {p: statistics.fmean(v) for p, v in grouped.items()}
    total = sum(means.values())
    if total <= 0:
        raise ValueError("Aggregated weights must have positive sum.")
    return {p: round(v / total, 6) for p, v in means.items()}


@dataclass(frozen=True)
class CompatibilityResponse:
    expert_id: str
    fault_code: str
    action_id: str
    compatibility: float
    confidence: float
    rationale: str
    provider: str = "synthetic"
    development_only: bool = True

    def to_dict(self):
        return asdict(self)


def aggregate_compatibility(
    responses: List[CompatibilityResponse],
) -> Dict[str, float]:
    """Return mean compatibility by fault/action pair."""
    grouped: Dict[str, List[float]] = {}
    for r in responses:
        if not (0 <= r.compatibility <= 1):
            raise ValueError("Compatibility must be in [0,1].")
        key = f"{r.fault_code}|{r.action_id}"
        grouped.setdefault(key, []).append(r.compatibility)
    return {k: round(statistics.fmean(v), 6) for k, v in grouped.items()}
