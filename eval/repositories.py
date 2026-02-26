import json
import os

from eval.domain import GoldenId
from eval.errors import GoldenSetNotFoundError
from eval.schemas.golden import GoldenSet


class GoldenRepository:
    def __init__(self, base_dir: str = "scenarios/goldens"):
        self.base_dir = base_dir

    def load_golden_set(self, golden_id: GoldenId) -> GoldenSet:
        # Try with .json extension if not present
        if not golden_id.endswith(".json"):
            filename = f"{golden_id}.json"
        else:
            filename = golden_id

        path = os.path.join(self.base_dir, filename)
        if not os.path.exists(path):
            raise GoldenSetNotFoundError(f"Golden set not found at {path}")
        with open(path) as f:
            return GoldenSet(**json.load(f))

    def exists(self, golden_id: GoldenId) -> bool:
        if not golden_id.endswith(".json"):
            filename = f"{golden_id}.json"
        else:
            filename = golden_id

        path = os.path.join(self.base_dir, filename)
        return os.path.exists(path)


# Default global instance for convenience, matching the previous module-level behavior
default_golden_repo = GoldenRepository()


def load_golden_set(golden_id: GoldenId) -> GoldenSet:
    """Convenience wrapper for the default repository."""
    return default_golden_repo.load_golden_set(golden_id)
