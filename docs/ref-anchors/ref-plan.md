# Refactoring Plan: Unify Anchor and Metadata in Evaluation Pipeline

## 1. Problem Statement
Currently, the evaluation pipeline splits `Anchor` entities into separate, parallel data structures (a list of anchor IDs and a dictionary mapping IDs to metadata). The function `select_anchors` in `eval/anchors.py` explicitly states it extracts these into a "legacy tuple shape for boundary compatibility." 

This creates a parallel array/dictionary anti-pattern in the `AnchorSelection` schema and forces downstream consumers (like the load generator and slicing evaluators) to pass around and synchronize two separate fields.

## 2. Goals
- Eliminate the legacy tuple return shape in `select_anchors`.
- Replace the parallel `anchors` and `anchor_metadata` fields in the `AnchorSelection` schema with a single list of holistic `Anchor` objects.
- Simplify downstream evaluation scripts to iterate over `Anchor` objects directly.
- Maintain data integrity by bumping the `anchors_schema_version` to `2.0`.

## 3. Implementation Steps

### Step 1: Update `eval/anchors.py`
Refactor `select_anchors` to return a `list[Anchor]` instead of `tuple[list[str], dict[str, dict[str, Any]]]`.
```python
def select_anchors(inputs: AnchorSelectionInputs) -> list[Anchor]:
    if inputs.count == 0:
        return []

    available = _available_anchors(inputs.dataset_id, inputs.scenario_id)
    rng = random.Random(f"{inputs.dataset_id}:{inputs.scenario_id}:{inputs.seed}")
    
    indices = list(range(len(available)))
    rng.shuffle(indices)
    
    selected_indices = indices[: min(inputs.count, len(indices))]
    return [available[i] for i in selected_indices]
```

### Step 2: Update the Raw Schema (`eval/schemas/raw.py`)
Bump the schema version and replace the parallel fields with a unified `list[Anchor]`.
```python
from eval.anchors import Anchor

class AnchorSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchors_schema_version: str = Field(default="2.0", min_length=1)  # Bump to 2.0
    run_id: str = Field(..., min_length=1)
    scenario_id: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    seed: int = Field(..., ge=0)
    
    # Store holistic objects
    anchors: list[Anchor] = Field(default_factory=list)
    # Remove anchor_metadata entirely
```

### Step 3: Update Orchestrator (`scripts/eval_orchestrator.py`)
Modify the orchestrator to pass the unified list directly to the `AnchorSelection` model, removing the tuple unpacking.
```python
# Select anchors
anchors = select_anchors(
    AnchorSelectionInputs(
        dataset_id=DatasetId(ctx.dataset_id),
        scenario_id=ScenarioId(ctx.scenario_id),
        seed=ctx.seed,
        count=ctx.anchor_count,
    )
)

# Write to context
write_anchor_selection(ctx, anchors)
```

### Step 4: Streamline Downstream Consumers
- **`eval/slicing.py`**: Update rule evaluation to accept an `Anchor` object instead of separate `anchor_id` and `metadata` parameters.
- **`eval/loadgen.py` & Evaluator Scripts**: Refactor loops to iterate over `anchor in anchors_selection.anchors`, accessing `anchor.id` and `anchor.metadata` directly instead of looking up the ID in the separate metadata dictionary.

### Step 5: Update Tests
- **`tests/unit/eval_platform/test_anchors.py`**: Update to check `list[Anchor]`.
- **`tests/unit/eval_platform/test_schemas.py`**: Update valid schema payload testing for `anchors.json`.
- **`tests/unit/eval_platform/test_rendering.py`**: Update expected mocked artifacts to `list[Anchor]`.
- **`tests/integration/eval_platform/test_stage0_acceptance.py`**: Update e2e test payloads.
- **`tests/integration/eval_platform/test_stage4_acceptance.py`**: Update e2e test payloads.

## 4. Success Criteria
- [ ] `select_anchors` returns `list[Anchor]`.
- [ ] `AnchorSelection` stores `list[Anchor]` and uses schema version `2.0`.
- [ ] All CI tests and evaluation pipelines pass with the unified schema.
