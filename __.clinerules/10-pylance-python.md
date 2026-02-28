---
description: Pylance/Bifrost workflow for Python changes
alwaysApply: false
paths:
  - "**/*.py"
---
# Python LSP Workflow

Treat the Bifrost MCP language server as the primary source for symbol-aware navigation and refactoring. Avoid manual text search (`rg`) for Python symbols unless LSP tools fail.

## 1. Primary Tool Mapping
Always use these tools before and during edits:
- **Discovery**: `get_workspace_symbols`, `get_document_symbols`
- **Navigation**: `go_to_definition`, `get_type_definition`, `get_declaration`
- **Context**: `get_hover_info`, `get_signature_help`, `get_completions`
- **Impact Analysis**: `find_usages`, `get_document_highlights`, `get_call_hierarchy`, `get_type_hierarchy`
- **Refactoring**: 
  - Renames: `get_rename_locations` + `rename` (never manual multi-file replace)
  - Structural: `get_selection_range`, `get_code_actions`, `find_implementations`

## 2. Validation & Typing
- Treat Pylance diagnostics as mandatory. Resolve any new errors before completing tasks.
- Add explicit type annotations in new/changed code when inference is ambiguous.
- Verify inferred types via `get_hover_info` before modifying overrides or protocols.

## 3. Fallback Mode
If the LSP index is unavailable or fails to resolve a symbol:
1. Explicitly state this limitation in your response.
2. Fall back to `list_code_definition_names`, focused file reads, and `rg`.
3. Perform conservative manual updates and verify all call sites.
4. Limit `rg` exclusively to non-symbol content (docs/strings/config) or when LSP fails.