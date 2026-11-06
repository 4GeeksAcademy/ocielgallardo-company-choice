# Informe de seguridad IA NIST — HealthCore (Hito 29)

Mapea los sistemas de IA actuales a las funciones NIST CSF. Marco regulatorio de [healthcore-BRIEFING.es.md](./healthcore-BRIEFING.es.md) §2 — **HIPAA (EE. UU.)** y **UK GDPR (Reino Unido) son regímenes separados**.

**Sin PHI** en este informe ni en artefactos de prueba (solo IDs sintéticos).

Documentos relacionados: [ai-systems-inventory.es.md](./ai-systems-inventory.es.md), [nist-protect-checklist.es.md](./nist-protect-checklist.es.md), [owasp-top10-report.es.md](./owasp-top10-report.es.md).

---

## Govern

**Acción concreta (este ciclo):** Matriz de responsables + política dual en el [inventario IA](./ai-systems-inventory.es.md); regla BRIEFING — auditar que ocurrió una acción, nunca guardar contenido clínico en traces.

---

## Identify

**Acción concreta (este ciclo):** Inventario completo de agentes, RAG, MCP, workflows RFP y componentes BRIEFING §3 N/A con riesgos. Ver [ai-systems-inventory.es.md](./ai-systems-inventory.es.md).

---

## Protect

**Acción concreta (este ciclo):** Guardrails de injection/PHI; **rate limiting** en `POST /agent/query`; secretos en env/`*_FILE`; delimitadores UNTRUSTED en RAG; outputs MCP tipados; HITL RFP.

| Control | Evidencia |
| --- | --- |
| Sanitización / rechazo injection | `agent_guardrails.py`; `tests/test_agent_injection.py` |
| Contexto no confiable | `<<<UNTRUSTED_REFERENCE_*>>>` en `rag.py` |
| Secretos | `.env.example` — sin keys hardcodeadas |
| Rate limit | `rate_limit.py` + `tests/test_agent_rate_limit.py` |
| Validación de tools | Pydantic en `agent_tools.py` / `_tool_facts_text` |
| Acciones irreversibles (§5) | SOAP/notificar paciente N/A; RFP exige Approve humano |
| Sin PHI en logs | Solo `question_chars` en traces/excepciones |

---

## Detect

**Acción concreta (este ciclo):** Spans `refuse_security`, respuestas **429**, y `auth_failure_rate` de telemetría como señales de abuso/anomalía.

---

## Respond

**Acción concreta (este ciclo):** Playbook dual (BRIEFING §2), tickets sin PHI.

| País de clínica | Notificar | Plazo |
| --- | --- | --- |
| Estados Unidos | Proceso HIPAA | Hasta **60 días** |
| Reino Unido | ICO (+ UK GDPR) | **72 horas** |

1. Endurecer rate limit / deshabilitar endpoint afectado.
2. Rotar `LLM_API_KEY` y secretos de servicio.
3. Conservar `trace_id` + spans (sin prompts/PHI).
4. Ramificar plazos por país — no unificar HIPAA y UK GDPR.

---

## Recover

**Acción concreta (este ciclo):**

1. `docker compose up` para `backend` / `mcp` / worker.
2. Volumen `rfp_langgraph_checkpoints` para continuidad HITL.
3. Re-seed de service clients tras rotación de secretos.
4. Smoke: `test_agent_injection.py` + `test_agent_rate_limit.py`.

---

## Brechas residuales (no corregidas este ciclo)

| Brecha | Riesgo | Mitigación propuesta | Prioridad |
| --- | --- | --- | --- |
| JWT en query string del WebSocket | Fuga en logs de proxy | Ticket de corta vida / subprotocolo | P1 |
| Rate limiter solo en memoria | Bypass multi-réplica | Bucket Redis compartido | P2 |
| SOAP / referidos / audit PHI N/A | Inventario BRIEFING incompleto en producto | Construir con HITL médico + audit metadata-only | P1 |
| Routing por regex | Menor precisión de intent | Clasificador LLM tras guardrails | P3 |
