# Eval Domain Centralization

## Decision
Adopt a centralized eval domain/contract view, with strict separation between:
- **Domain layer**: internal types, entities, and domain errors.
- **Wire/schema layer**: persisted artifact payloads and API-facing schemas.

This is a **yes** to centralization, but implemented incrementally to preserve current behavior and artifact compatibility.

## Why
- Current anchor logic mixes domain behavior and filesystem concerns in `eval/anchors.py`.
- Existing eval schemas are partially centralized under `eval/schemas/*`, but anchor-domain concepts are not represented consistently.
- A centralized view improves testability, static typing, error semantics, and change safety.

## Scope
Applies to the eval platform in this repository:
- `eval/anchors.py`
- `eval/schemas/*`
- orchestrator and tests consuming anchor selection outputs

Does not require immediate changes to:
- run directory structure
- existing artifact file names
- existing `raw/anchors.json` field shape in Phase A

## Target Architecture

### 1) Domain Layer
New modules:
- `eval/domain.py`: value types (`DatasetId`, `ScenarioId`, `AnchorId`, `GoldenId`)
- `eval/errors.py`: domain exception hierarchy
- `eval/anchors_domain.py` (or equivalent): internal `Anchor` entity + pure selection logic
- `eval/golden_repository.py` (or equivalent): I/O boundary for loading golden sets

Rules:
- Domain exceptions subclass `ValueError` during migration.
- Domain logic should be deterministic and independent of filesystem state.
- Domain entities can be richer than wire payloads.

### 2) Wire/Schema Layer
`eval/schemas/*` remains the source of truth for persisted and exchanged payloads.

Rules:
- `eval/schemas/raw.py` defines artifact contract fields.
- Schema versions are explicit.
- Backward compatibility is default unless a versioned migration is declared.

### 3) Mapping Boundary
Explicit mapping from domain entities to wire payloads:
- Internal `list[Anchor]` -> persisted `anchors` + `anchor_metadata` (Phase A)
- Future schema changes require version bump + transition strategy

## Compatibility Policy

### Phase A (Required)
- Preserve current `raw/anchors.json` shape.
- Keep orchestrator consumers unchanged.
- Keep `except ValueError` behavior working.

### Phase B (Optional)
- If serializing structured anchors directly, bump `anchors_schema_version`.
- Implement transition support (dual-read or migration tool).
- Update docs/tests/consumers before removing old format support.

## Testing Expectations
- Deterministic selection tests remain.
- Domain-specific error tests added.
- Compatibility tests ensure `ValueError` catches still work.
- Artifact contract tests assert `anchors` and `anchor_metadata` remain stable in Phase A.

## Decision Record Summary
- **Status**: accepted
- **Date**: 2026-02-26
- **Owner**: eval platform maintainers
- **Risk posture**: compatibility-first, staged migration
