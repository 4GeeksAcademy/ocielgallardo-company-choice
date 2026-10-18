"""HealthCore incidents + inventory MCP server (OAuth-protected resource).

Exposes the operational tools the support agent needs over the Model Context
Protocol (Streamable HTTP): incident lookups and writes, and read-only
inventory stock lookups. Authentication is OAuth 2.1 via MCP Auth
(``mcpauth``): RS256 tokens minted by the HealthCore API
(``POST /auth/token``) are verified against the API's JWKS and this server
publishes RFC 9728 protected-resource metadata.

Modules:
- ``auth``: MCP Auth wiring (PRM, bearer middleware, verified ``AuthInfo``).
- ``permissions``: per-tool scope checks over the verified identity.
- ``backend_client``: single HTTP choke point + endpoint allowlist.
- ``server``: FastMCP server, tools and transport security.
- ``app``: ASGI app (MCP Auth in front of Streamable HTTP + health).
"""

__all__ = ["app", "auth", "backend_client", "permissions", "server"]
