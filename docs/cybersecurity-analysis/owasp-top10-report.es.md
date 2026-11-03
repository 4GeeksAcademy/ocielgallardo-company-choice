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

## Residuales documentados

RBAC completo de inventario/proveedores, tokens MCP por usuario, JWT fuera del query string WS, concurrencia TinyDB — seguimientos, no bloquean el sign-off de críticos de este hito.
