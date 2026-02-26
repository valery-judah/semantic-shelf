import random
from dataclasses import dataclass


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


def available_anchors(dataset_id: str, scenario_id: str) -> list[str]:
    dataset_anchors = _ANCHOR_CATALOG.get(dataset_id, {})
    anchors = dataset_anchors.get(scenario_id)
    if anchors is None:
        raise ValueError(f"No anchor catalog for dataset_id={dataset_id} scenario_id={scenario_id}")
    return anchors.copy()


def select_anchors(inputs: AnchorSelectionInputs) -> list[str]:
    anchors = available_anchors(inputs.dataset_id, inputs.scenario_id)
    if inputs.count <= 0:
        return []

    rng = random.Random(f"{inputs.dataset_id}:{inputs.scenario_id}:{inputs.seed}")
    shuffled = anchors.copy()
    rng.shuffle(shuffled)
    return shuffled[: min(inputs.count, len(shuffled))]
