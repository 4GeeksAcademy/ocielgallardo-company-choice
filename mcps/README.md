# `mcps` folder

This folder contains **Model Context Protocol (MCP) Servers** that expose tools, resources, and context to AI models and agents.

Each subfolder inside `mcps/` must correspond to **one specific MCP server** (for example: `database-mcp`, `github-mcp`) and include its own documentation.

- **Main purpose**: to centralize the servers that bridge the gap between AI models and the company's internal systems or data sources.
- **Recommendation**: document the tools and resources exposed by each MCP server.

## Servers

| Server | Exposes | Auth |
| ------ | ------- | ---- |
| [`incidents-inventory-mcp/`](./incidents-inventory-mcp/README.md) | Incident lookups + writes, inventory stock lookups (read-only) for the support agent | OAuth resource server (RFC 9728), service JWT, per-tool scopes |

> _Spanish version: [README.es.md](./README.es.md)._
