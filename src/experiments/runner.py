
"""Step 15: reproducible experiment contracts and baseline interfaces.

This module intentionally does not train a final model or use the 100-incident
pilot as final empirical evidence. It establishes the interfaces needed for
the scaled scenario-based experiment.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Mapping, Sequence
import hashlib
import json


@dataclass(frozen=True)
class ExperimentSpec:
    experiment_id: str
    approach: str
    scenario_id: str
    fault_category: str
    topology_id: str
    split: str
    run_number: int
    random_seed: int

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Prediction:
    incident_id: str
    approach: str
    predicted_action: str
    confidence: float
    model_version: str

    def to_dict(self):
        return asdict(self)


class Baseline:
    """Minimal baseline contract; implementations must be deterministic."""

    name = "BASELINE"

    def predict(self, context: Mapping[str, Any]) -> Prediction:
        raise NotImplementedError


class RuleBasedBaseline(Baseline):
    name = "rule_based"

    def predict(self, context):
        action = context.get("selected_action_reference")
        if action is None:
            action = "NO_ACTION"
        return Prediction(
            incident_id=str(context["incident_id"]),
            approach=self.name,
            predicted_action=str(action),
            confidence=1.0,
            model_version="RB-dev-v1",
        )


class RandomForestBaseline(Baseline):
    name = "rf"

    def predict(self, context):
        """Interface placeholder until a final RF is trained/frozen."""
        raise RuntimeError(
            "RF is intentionally not trained in Step 15. "
            "Train/freeze it on development data before final experiments."
        )


class GARDMBaseline(Baseline):
    name = "gardm"

    def predict(self, context):
        action = context.get("selected_action")
        if action is None:
            action = "NO_ACTION"
        return Prediction(
            incident_id=str(context["incident_id"]),
            approach=self.name,
            predicted_action=str(action),
            confidence=float(context.get("decision_confidence", 0.0)),
            model_version=str(context.get("model_version", "GARDM-dev")),
        )


class ExperimentRunner:
    """Create deterministic experiment manifests without executing final claims."""

    def __init__(self, seed: int = 42):
        self.seed = int(seed)

    @staticmethod
    def make_experiment_id(
        approach: str, scenario_id: str, split: str, run_number: int, seed: int
    ) -> str:
        raw = f"{approach}|{scenario_id}|{split}|{run_number}|{seed}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:12]
        return f"EXP-{digest}"

    def manifest(
        self,
        approaches: Sequence[str],
        scenarios: Sequence[Mapping[str, Any]],
        split: str,
        run_number: int = 1,
    ) -> List[ExperimentSpec]:
        rows = []
        for scenario in scenarios:
            for approach in approaches:
                eid = self.make_experiment_id(
                    approach, str(scenario["scenario_id"]), split, run_number, self.seed
                )
                rows.append(ExperimentSpec(
                    experiment_id=eid,
                    approach=approach,
                    scenario_id=str(scenario["scenario_id"]),
                    fault_category=str(scenario["fault_category"]),
                    topology_id=str(scenario["topology_id"]),
                    split=split,
                    run_number=run_number,
                    random_seed=self.seed,
                ))
        return rows
