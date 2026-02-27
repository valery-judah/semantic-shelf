# Python MCP Server Setup (Bifrost)

This document covers the configuration and mandates for using the VS Code Bifrost extension as a Python language MCP server for AI agents (like Roo Code or Cline) in this project.

## Pylance Mandates and Agent Rules

According to `.clinerules/10-pylance-python.md`, agents must adhere to the following rules:
- **Mandatory Server:** Agents MUST use this Bifrost server for symbol-aware navigation and refactoring.
- **LSP Tooling Over Text Search:** Language Server Protocol (LSP) tools (`go_to_definition`, `find_usages`, etc.) should be favored over manual text searches (like `rg` or regex) for understanding and modifying code.
- **Pylance Diagnostics:** Pylance diagnostics are mandatory. Agents must ensure that their changes do not introduce Pylance errors.

## Installation and Startup

1. **Install VS Code Extensions:**
   - Install the `ConnorHallman.bifrost-mcp` extension.
   - Install the required language extensions for this project (Python and Pylance).
2. **Open Project:** Open this project in VS Code.
3. **Start the Server:**
   - The server is started manually via the VS Code command palette: `Bifrost MCP: Start Server`.
   - The default endpoint is `http://localhost:8008/sse`.

*(Optional: If your project uses `bifrost.config.json` with a custom `port` and `path`, use the endpoint `http://localhost:<port>/<path>/sse`)*

## MCP Configuration

Depending on the AI agent you are using, you need to configure the MCP server settings to automatically allow or approve the Bifrost tools.

### Roo Code Configuration

For Roo Code, configure the server in `.roo/mcp.json` using the `alwaysAllow` array:

```json
{
  "mcpServers": {
    "Bifrost": {
      "url": "http://localhost:8008/sse",
      "alwaysAllow": [
        "find_usages",
        "go_to_definition",
        "find_implementations",
        "get_hover_info",
        "get_document_symbols",
        "get_completions",
        "get_signature_help",
        "get_rename_locations",
        "rename",
        "get_code_actions",
        "get_semantic_tokens",
        "get_call_hierarchy",
        "get_type_hierarchy",
        "get_code_lens",
        "get_selection_range",
        "get_type_definition",
        "get_declaration",
        "get_document_highlights",
        "get_workspace_symbols"
      ]
    }
  }
}
```

### Cline Configuration

For Cline, configure the server in `cline_mcp_settings.json` using the `autoApprove` array:

```json
{
  "mcpServers": {
    "Bifrost": {
      "url": "http://localhost:8008/sse",
      "autoApprove": [
        "find_usages",
        "go_to_definition",
        "find_implementations",
        "get_hover_info",
        "get_document_symbols",
        "get_completions",
        "get_signature_help",
        "get_rename_locations",
        "rename",
        "get_code_actions",
        "get_semantic_tokens",
        "get_call_hierarchy",
        "get_type_hierarchy",
        "get_code_lens",
        "get_selection_range",
        "get_type_definition",
        "get_declaration",
        "get_document_highlights",
        "get_workspace_symbols"
      ]
    }
  }
}
```

## Troubleshooting

- **Connection Issues:** If the agent cannot connect, verify the Bifrost server is running (check VS Code output or command palette) and the endpoint matches the active port/path.
- **Limited Data:** If symbol tools return limited data, verify the Python and Pylance extensions are fully loaded, installed, and the workspace is fully indexed by Pylance.
- **Reloading:** You may need to reload the VS Code window or restart the agent extension after changing MCP settings.
