# Cline Rules Layout

This repository uses folder-based Cline rules (`.clinerules/`) with conditional frontmatter.

- `10-pylance-python.md`: applies a Pylance-first workflow to Python files, with explicit fallback behavior when LSP tools are unavailable in the current runtime.
- `docs/bifrost-mcp-cline-setup.md`: installation and MCP configuration reference for Bifrost + Cline.

To add more scoped behavior, create additional `.md` rule files with `paths` and `alwaysApply` settings.

Note: Cline can only use tools exposed in its active tool runtime. Full "Go to Definition / Find References / Rename Symbol" flows require an IDE/LSP or MCP integration that surfaces those capabilities.
