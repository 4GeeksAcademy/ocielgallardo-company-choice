# Informe OWASP Top 10 — HealthCore

**Proyecto:** `ai-eng-cybersecurity-vulnerabilities`  
**Rama:** `feature/owasp-top10-audit`  
**BRIEFING:** [healthcore-BRIEFING.es.md](./healthcore-BRIEFING.es.md) §7  
**Regla de evidencia:** sin PHI ni identificadores de paciente reales (solo IDs sintéticos).

## Inventario (BRIEFING §3)

| Componente | ¿En el fork? | Nota |
| --- | --- | --- |
| Asistente documentación clínica (SOAP) | **N/A** | No implementado |
| Flujo de referidos a paciente | **N/A** | Solo KB de proceso |
| RAG de políticas | **Sí** | API + agente |
| Agente compliance / knowledge | **Sí** | LangGraph + WebSocket |
| Sistema de auditoría de accesos | **N/A** | Placeholder |
| Dashboard KPI clínico SSE | **N/A** | Reporting REST de supply |
| Frontend staff | **Sí** | `uis/backoffice` |

Tres carriles por categoría: **API/Backend** | **Frontend/Staff UI** | **Agentic/AI**. Detalle completo en [owasp-top10-report.md](./owasp-top10-report.md).

## Resumen de correcciones críticas

| ID | Categoría | Corrección | Evidencia |
| --- | --- | --- | --- |
| C1 | A01 | Auth en analyze/export de incidencias y report telemetry | `incidents.py`, `telemetry.py`, tests |
| C2 | A01 | Aprobación RFP por departamento / admin | `departments.py`, `rfp.py` |
| C3 | A01 | Registro público desactivable | `ALLOW_PUBLIC_REGISTRATION` |
| C4 | A01 | Chat WS solo staff | `agent.py` + test rol |
| C5 | A05 | Redis/Qdrant/Flower sin puertos host; USER no-root; docs off en prod | compose + Dockerfiles + `main.py` |
| C6 | A03/Agentic | Refuse injection + gate PHI + delimiters RAG | `agent_guardrails.py`, `rag.py`, `test_agent_injection.py` |
| C7 | Baseline | Scripts SSH/UFW + runbook | `scripts/hardening/`, `server-hardening.es.md` |

## Evidencia antes / después (reproducible)

Sin PHI en comandos ni fixtures (solo IDs sintéticos).

| ID | Hallazgo crítico | Antes | Después (reproducir) |
| --- | --- | --- | --- |
| C1 | Incidents analyze/export abiertos | Sin Bearer aceptaban tráfico | `pytest tests/test_owasp_access_control.py::test_incidents_*` → **401** |
| C2 | Telemetry report abierto | Sin JWT devolvía métricas | `…::test_telemetry_report_requires_auth` → **401** |
| C3 | Registro abierto | `POST /users` siempre | `ALLOW_PUBLIC_REGISTRATION=false` → **403** |
| C4 | Aprobación RFP sin dueño | Cualquier JWT | `test_department_approval_requires_owner_or_admin` |
| C5 | WS compliance cualquier user | Rol `user` entraba | `test_ws_rejects_non_staff_role` |
| C6 | Redis/Qdrant/Flower en host | `ports` publicados | `expose` only; test Flower sin `"5555:5555"` |
| C7 | Prompt injection | Llegaba al LLM | `tests/test_agent_injection.py` + `refuse_security` |
| C8 | SSH root / firewall / carpetas planas | Defaults Linux | `scripts/hardening/*` + `verify-baseline.sh` (dirs 750/700) |

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/telemetry/report
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/api/incidents/analyze
```

Detalle EN: [owasp-top10-report.md](./owasp-top10-report.md).

## Residuales documentados

RBAC completo de inventario/proveedores, tokens MCP por usuario, JWT fuera del query string WS, concurrencia TinyDB — seguimientos, no bloquean el sign-off de críticos de este hito.
