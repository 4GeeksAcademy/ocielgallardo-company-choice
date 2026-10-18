# Servidor MCP de incidentes e inventario

Servidor **Model Context Protocol** protegido con OAuth que expone las
herramientas operativas de HealthCore que necesita el agente de soporte:
consultas y altas/modificaciones de incidentes, y consulta de stock de
inventario (solo lectura). Es un proceso independiente (servicio `mcp` en
Compose, puerto `8100`) frente a la API existente — sin nuevas rutas de datos
ni nuevas reglas de negocio.

> _Inglés: [README.md](./README.md)._

## Herramientas y scopes

| Herramienta | Argumentos | Scope | Notas |
|-------------|-----------|-------|-------|
| `get_incident_status` | `ticket_id` | `incidents:read` | Un incidente por id |
| `list_incidents` | `status`, `origin`, `branch`, `category` (al menos uno) | `incidents:read` | Filtros exactos |
| `create_incident` | `title`, `description`, `category`, `origin`, `branch` | `incidents:write` | La API valida los enums |
| `update_incident_status` | `ticket_id`, `status` | `incidents:write` | La API valida la transición |
| `get_inventory_stock` | `supply_id` o `sku` o `name_query` | `inventory:read` | Consultas de stock (solo lectura) |
| `update_inventory_stock` | `supply_id`, `quantity_change`, `reason` | — | **Siempre rechaza** (`inventory_write_denied`); nunca toca la backend |

Todas las respuestas usan los contratos existentes del agente
(`IncidentToolOutput` / `InventoryToolOutput` de
`data/pipelines/agent_tools.py`): `ok`, payload y `error` ∈
`not_found | timeout | unavailable | invalid_input | auth`. Los fallos se
reportan como datos de la herramienta, nunca como estado inventado. Los tipos
de retorno están anotados (`structured_output=True`), por lo que `tools/list`
anuncia un `outputSchema` y las llamadas exitosas responden con
`structuredContent`.

## Modelo de seguridad

- **Servidor de recursos OAuth (RFC 9728) vía MCP Auth (`mcpauth`).** `/mcp`
  exige bearer token; los `401`/`403` incluyen
  `WWW-Authenticate: … resource_metadata="…"` y los metadatos se sirven en
  `/.well-known/oauth-protected-resource/mcp`, apuntando la autorización a la
  API de HealthCore (`MCP_AUTH_ISSUER_URL`).
- **Validación del token.** MCP Auth obtiene el
  `/.well-known/openid-configuration` del issuer al arrancar y valida cada
  token contra su JWKS (RS256): `iss` debe ser el issuer y `aud` debe ser este
  recurso (`MCP_RESOURCE_URL`, RFC 8707). Solo pueden validar tokens RS256
  emitidos por el grant de client-credentials de la API; los tokens de sesión
  humana (HS256) no. Sin secreto simétrico compartido en este proceso.
- **Autorización por herramienta.** MCP Auth guarda la identidad verificada
  (`AuthInfo`: subject, client_id, scopes) en una variable de contexto; cada
  herramienta comprueba su propio scope (`permissions.require_scopes`),
  cerrando por defecto si no hay identidad. Las denegaciones son errores
  explícitos (`insufficient_scope: missing …`), nunca fallos silenciosos.
- **Identidad hacia la API.** El servidor se autentica con su propia identidad
  de servicio (`MCP_BACKEND_CLIENT_ID` / `MCP_BACKEND_CLIENT_SECRET`, opcional
  `…_FILE`), de modo que una llamada MCP jamás escribe con un scope no
  otorgado. El inventario es de solo lectura en cinco capas: una herramienta
  de rechazo (`update_inventory_stock` → `inventory_write_denied`), el gate de
  scopes, la lista de endpoints solo-GET en `backend_client`, la ausencia de
  helpers de escritura en el módulo del servidor y las rutas de escritura
  solo-humanas en la API.
- **Auditoría.** Cada llamada a una herramienta registra
  `tool= client= result= ms=`, incluidas las denegaciones por scope y por
  política de solo lectura (`result=denied_scope` / `result=denied_policy`).

## Catálogo de errores

A nivel de transporte (antes de ejecutar ninguna herramienta; códigos OAuth en
el cuerpo JSON y en `WWW-Authenticate`):

| Código | HTTP | Significado |
|--------|------|-------------|
| `missing_auth_header` | 401 | Sin cabecera `Authorization` |
| `invalid_auth_header_format` | 401 | La cabecera no es `Bearer <token>` |
| `missing_bearer_token` | 401 | `Bearer` con token vacío |
| `invalid_token` | 401 | Firma incorrecta, expirado, malformado o no verificable contra el JWKS del issuer |
| `invalid_issuer` | 401 | El `iss` del token no es el servidor de autorización configurado |
| `invalid_audience` | 401 | El `aud` del token no es este recurso (`MCP_RESOURCE_URL`) |

A nivel de herramienta (token válido; autorización o resultado de contrato):

| Marcador | Dónde | Significado |
|----------|-------|-------------|
| `insufficient_scope: missing <scope>` | error de herramienta (`isError`) | Al token le falta el scope que exige la herramienta |
| `inventory_write_denied` | error de herramienta (`isError`) | Rechazo explícito de solo lectura de `update_inventory_stock` |
| `not_found` / `timeout` / `unavailable` / `invalid_input` / `auth` | payload de contrato (`ok: false`) | Resultado de la backend reportado como dato, no como error de protocolo |
| `Unknown tool` | error de herramienta | Nombre de herramienta no registrado |

## Configuración

| Variable | Propósito | Defecto |
|----------|-----------|---------|
| `MCP_AUTH_ISSUER_URL` | Servidor de autorización cuyo discovery + JWKS se obtienen al arrancar | `http://localhost:8000` |
| `MCP_RESOURCE_URL` | Identidad de este recurso; también el `aud` exigido al token | `http://localhost:8100/mcp` |
| `MCP_BACKEND_URL` | URL base de la API | `http://127.0.0.1:8000` |
| `MCP_BACKEND_CLIENT_ID` / `_SECRET` / `_SECRET_FILE` | Identidad propia del servidor | — |
| `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS` | Allowlists contra DNS rebinding (los defectos cubren loopback, `mcp`, `testserver`, `*.github.dev`) | — |

Todo llega del entorno (Compose pasa `.env`); el servidor no guarda
credenciales. El issuer debe ser accesible al construir la app (obtención al
arrancar). `SECRET_KEY` **no** se usa en este proceso.

## Ejecutar

Local (desde la raíz del repo, API ya en `:8000`):

```bash
PYTHONPATH=. uv run uvicorn incidents_inventory_mcp.app:app \
    --app-dir mcps/incidents-inventory-mcp --port 8100
```

Registrar/rotar la identidad del servidor (imprime el secreto una vez):

```bash
PYTHONPATH=. uv run python scripts/seed_service_client.py \
    --client-id mcp-server --env-prefix MCP_BACKEND \
    --scopes incidents:read incidents:write inventory:read
```

Compose (misma imagen que la backend, URLs de red interna):

```bash
docker compose up --build mcp     # salud: curl http://localhost:8100/health
```

## Conectar un cliente

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "healthcore": {
        "transport": "streamable_http",
        "url": "http://127.0.0.1:8100/mcp",
        "headers": {"Authorization": f"Bearer {service_token}"},
    }
})
tools = await client.get_tools()          # 6 herramientas
result = await tools[0].ainvoke({...})
```

El token debe emitirse con `aud` igual a la URL del recurso (`POST /auth/token`
acepta un campo `audience`). Un cliente sin token válido recibe `401` con el
puntero a los metadatos; un token con `iss`/`aud` incorrectos recibe
`invalid_issuer`/`invalid_audience`; un token sin el scope necesario recibe un
error de herramienta `insufficient_scope` explícito.

## Pruebas

```bash
uv run python -m pytest tests/mcps -q     # auth, protocolo, scopes, invariantes de solo lectura
uv run python -m pytest tests/pipelines/test_mcp_client.py tests/pipelines/test_agent_graph_mcp.py -q
```

Decisiones de diseño y evidencia de aceptación en vivo:
`docs/rag/agent-graph.md` §4 (transporte MCP) y §9.2 (desviación de §9.1).
