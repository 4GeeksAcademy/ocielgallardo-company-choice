# Inventario de sistemas de IA — HealthCore

Fuente para Identify/Govern. Alineado con [healthcore-BRIEFING.es.md](./healthcore-BRIEFING.es.md) §§2–5.  
**Sin PHI** en este inventario.

## Nota regulatoria (BRIEFING §2)

| Régimen | Notificación | Acuerdo con procesador |
| --- | --- | --- |
| HIPAA (clínicas EE. UU.) | Hasta **60 días** | BAA (incl. proveedor LLM) |
| UK GDPR (clínicas Reino Unido) | **72 horas** al ICO | DPA |

Datos restringidos: PHI / identificadores de paciente no deben aparecer en logs, traces, eventos ni salidas de modelo retenidas para auditoría.

## Inventario (construido + BRIEFING §3)

| Componente | Entrypoints / rutas | Responsable | Proveedor tercero | Quién controla el control si el modelo/herramienta es de un tercero | Riesgo principal | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| Agente compliance / knowledge (LangGraph) | `POST /agent/query`, `WS /agent/chat/ws`; `agent_graph.py`, `agent_guardrails.py` | Cumplimiento — Claire Whitfield | LLM vía `LLM_API_*` | HealthCore retiene prompts/política; el vendor opera el modelo — BAA antes de PHI | Prompt injection directa; alucinación normativa | Implementado |
| RAG de políticas/protocolos | `POST /knowledge/query`; `rag.py`; Qdrant | Tecnología — James Osei | Embeddings `EMBEDDING_API_*`; LLM de generación | HealthCore posee corpus y filtros; vendors procesan texto bajo BAA/DPA | Prompt injection indirecta | Implementado |
| MCP incidentes/inventario | `mcps/incidents-inventory-mcp`; `mcp_client.py` | Tecnología — James Osei; oversight Compliance | MCP first-party; JWT de servicio | HealthCore posee schemas, scopes y allowlists | Agencia excesiva si hay writes | Implementado (agente **solo lecturas**) |
| RFP intake / classify / draft | `rfp_intake/*`; APIs `/rfp` | Sales/RFP + Compliance en secciones | LLM compartido | HealthCore posee reglas BRIEFING + HITL | PHI en RFP; docs sin aprobar | Implementado |
| RFP approval HITL | `approval_graph.py`; UI `/rfp` | Owners por departamento + admins | Checkpoints Sqlite locales | HealthCore posee interrupt/resume y ACL | Documento final sin humano | Implementado (confirmación humana) |
| Asistente documentación clínica (SOAP) | — | Operaciones clínicas — Dr. Marcus Reid | — | — | Fuga PHI | N/A |
| Referidos automatizados | — | Acceso paciente — Priya Nair | — | — | Notificar sin validación humana | N/A |
| Auditoría de acceso a historiales | — | Cumplimiento — Claire Whitfield | — | — | Logs con PHI | N/A |

## Artefactos relacionados

- Informe NIST: [nist-ai-security-report.es.md](./nist-ai-security-report.es.md)
- Checklist Protect: [nist-protect-checklist.es.md](./nist-protect-checklist.es.md)
