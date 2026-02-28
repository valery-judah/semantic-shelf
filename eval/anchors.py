import random

from pydantic import BaseModel, ConfigDict, Field

from eval.domain import AnchorId, DatasetId, GoldenId, ScenarioId
from eval.errors import AnchorNotFoundError, ScenarioMismatchError
from eval.repositories import default_golden_repo
from eval.schemas.raw import Anchor


class AnchorSelectionInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: DatasetId
    scenario_id: ScenarioId
    seed: int
    count: int = Field(ge=0)


_ANCHOR_CATALOG: dict[DatasetId, dict[ScenarioId, list[AnchorId]]] = {
    DatasetId("local_dev"): {
        ScenarioId("similar_books_smoke"): [AnchorId(str(i)) for i in range(1, 13)]
    }
}


def _available_anchors(dataset_id: DatasetId, scenario_id: ScenarioId) -> list[Anchor]:
    golden_id = GoldenId(dataset_id)
    if default_golden_repo.exists(golden_id):
        golden = default_golden_repo.load_golden_set(golden_id)
        if golden.scenario_id != scenario_id:
            raise ScenarioMismatchError(
                "Golden set scenario mismatch: "
                f"golden.scenario_id={golden.scenario_id} requested_scenario_id={scenario_id}"
            )
        return [Anchor(id=AnchorId(a.anchor_id), metadata=a.metadata) for a in golden.anchors]

    dataset_anchors = _ANCHOR_CATALOG.get(dataset_id, {})
    anchors = dataset_anchors.get(scenario_id)
    if anchors is None:
        raise AnchorNotFoundError(
            f"No anchor catalog for dataset_id={dataset_id} scenario_id={scenario_id}"
        )
    return [Anchor(id=aid) for aid in anchors]


def select_anchors(inputs: AnchorSelectionInputs) -> list[Anchor]:
    """
    Selects anchors based on deterministic shuffling.
    Returns:
        A list of Anchor objects.
    """
    if inputs.count == 0:
        return []

    available = _available_anchors(inputs.dataset_id, inputs.scenario_id)

    rng = random.Random(f"{inputs.dataset_id}:{inputs.scenario_id}:{inputs.seed}")

    # Shuffle internal Anchor entities
    indices = list(range(len(available)))
    rng.shuffle(indices)

    selected_indices = indices[: min(inputs.count, len(indices))]
    return [available[i] for i in selected_indices]
