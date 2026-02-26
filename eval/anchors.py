import json
import os
import random
from dataclasses import dataclass
from typing import Any

from eval.schemas.golden import GoldenSet


@dataclass(frozen=True)
class AnchorSelectionInputs:
    dataset_id: str
    scenario_id: str
    seed: int
    count: int


_ANCHOR_CATALOG: dict[str, dict[str, list[str]]] = {
    "local_dev": {
        "similar_books_smoke": [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
        ]
    }
}


def load_golden_set(golden_id: str) -> GoldenSet:
    # Try with .json extension if not present
    if not golden_id.endswith(".json"):
        filename = f"{golden_id}.json"
    else:
        filename = golden_id
        
    path = os.path.join("scenarios", "goldens", filename)
    if not os.path.exists(path):
        raise ValueError(f"Golden set not found at {path}")
    with open(path) as f:
        return GoldenSet(**json.load(f))


def available_anchors(dataset_id: str, scenario_id: str) -> tuple[list[str], dict[str, dict[str, Any]]]:
    # Check if dataset_id corresponds to a golden set file
    golden_path = os.path.join("scenarios", "goldens", f"{dataset_id}.json")
    if os.path.exists(golden_path):
        golden = load_golden_set(dataset_id)
        if golden.scenario_id != scenario_id:
            raise ValueError(
                "Golden set scenario mismatch: "
                f"golden.scenario_id={golden.scenario_id} requested_scenario_id={scenario_id}"
            )
        anchors = [a.anchor_id for a in golden.anchors]
        metadata = {a.anchor_id: a.metadata for a in golden.anchors}
        return anchors, metadata

    dataset_anchors = _ANCHOR_CATALOG.get(dataset_id, {})
    anchors = dataset_anchors.get(scenario_id)
    if anchors is None:
        raise ValueError(f"No anchor catalog for dataset_id={dataset_id} scenario_id={scenario_id}")
    return anchors.copy(), {}


def select_anchors(inputs: AnchorSelectionInputs) -> tuple[list[str], dict[str, dict[str, Any]]]:
    anchors, metadata = available_anchors(inputs.dataset_id, inputs.scenario_id)
    if inputs.count <= 0:
        return [], {}

    rng = random.Random(f"{inputs.dataset_id}:{inputs.scenario_id}:{inputs.seed}")
    
    # Use indices to shuffle so we can pick metadata later
    indices = list(range(len(anchors)))
    rng.shuffle(indices)
    
    selected_indices = indices[: min(inputs.count, len(indices))]
    selected_anchors = [anchors[i] for i in selected_indices]
    
    selected_metadata = {aid: metadata.get(aid, {}) for aid in selected_anchors}
    
    return selected_anchors, selected_metadata
