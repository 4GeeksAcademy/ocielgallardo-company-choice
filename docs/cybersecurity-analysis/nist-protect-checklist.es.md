# Checklist NIST Protect — HealthCore (Hito 29)

Alineado con BRIEFING §§2–6. Complementa el [informe OWASP](./owasp-top10-report.es.md).  
**Sin PHI** en este documento ni en artefactos de prueba.

## Regímenes regulatorios separados

| Tema | HIPAA (EE. UU.) | UK GDPR |
| --- | --- | --- |
| Plazo de notificación de brecha | Hasta **60 días** | **72 horas** al ICO |
| Autoridad | HHS / covered entity | ICO |
| Acuerdo con procesador | BAA (incl. proveedor LLM) | DPA |
| Derechos del paciente | Derechos individuales HIPAA | Derechos del interesado UK GDPR |

No son una política global única: el playbook de incidentes debe ramificar por país de la clínica.

## Inventario IA + responsables (BRIEFING §3)

| Componente | Responsable | Estado en el fork |
| --- | --- | --- |
| Asistente documentación clínica | Operaciones clínicas — Dr. Marcus Reid | N/A |
| Flujo de referidos automatizado | Acceso paciente — Priya Nair | N/A (solo KB) |
| RAG de protocolos/políticas | Tecnología — James Osei | Implementado |
| Agente de cumplimiento | Cumplimiento — Claire Whitfield | Implementado |
| Auditoría de accesos | Cumplimiento — Claire Whitfield | N/A |

## Ítems Protect

- [x] HIPAA y UK GDPR tratados por separado.
- [x] Inventario con responsables.
- [x] Caso de prompt injection bloqueado (`tests/test_agent_injection.py`, ID sintético `TEST-001`).
- [x] Contexto RAG marcado como UNTRUSTED REFERENCE.
- [x] Gate de salida ante patrones tipo PHI/SSN.
- [x] Acciones irreversibles §5: N/A donde no hay implementación; RFP exige HITL.
- [x] Sin PHI en traces/logs de agente (solo metadatos).

Controles de servidor: [server-hardening.es.md](./server-hardening.es.md).
