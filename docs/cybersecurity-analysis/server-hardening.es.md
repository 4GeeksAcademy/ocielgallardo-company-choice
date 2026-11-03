# Baseline de servidor / red — HealthCore (Hito 29)

Endurecimiento académico para `ai-eng-cybersecurity-vulnerabilities` (BRIEFING §7).  
**Sin PHI** en la evidencia. Preferir Codespaces o Ubuntu para SSH/UFW; en Windows usar los controles de Compose descritos abajo.

## Objetivos (acceptance)

| Control | Evidencia |
| --- | --- |
| Sin login SSH directo como root | `PermitRootLogin no` vía `scripts/hardening/` |
| Usuario deploy no-root | `healthcore` (o `DEPLOY_USER`) con sudo |
| Permisos explícitos de carpetas | `/opt/healthcore/{app,logs,secrets,config}` modos 750/750/700/750 |
| Firewall con puertos mínimos | UFW: solo 22, 80, 443 |
| APIs/dashboards sin exponer DB/colas/admin | Compose: Redis, Qdrant, Flower **sin** puertos en el host |

## Linux / Codespaces (host)

```bash
sudo bash scripts/hardening/harden-linux-baseline.sh
sudo bash scripts/hardening/verify-baseline.sh
```

### Separación de carpetas

Bajo `HEALTHCORE_ROOT` (por defecto `/opt/healthcore`): `app/` (750), `logs/` (750), `secrets/` (700), `config/` (750).  
Mapeo Compose: código en `app/`; `.env` y `data/process/auth/` en `secrets/`; logs en `logs/`.

### Limitación en Windows

Los scripts **salen en no-Linux**. Captura evidencia SSH/UFW/carpetas en Codespaces; el lockdown de puertos Compose es el control verificable en el monorepo desde Windows.

## Mapeo Compose (firewall en-repo)

| Servicio | Puertos host (compose prod) | Motivo |
| --- | --- | --- |
| website / backoffice | 3000, 3001 | UI staff / pública |
| backend API | 8000 | API clínica/staff |
| MCP | 8100 | Tools con OAuth |
| redis / qdrant / flower | **ninguno** | Solo red interna |

## Contenedores no-root y docs API

- Imágenes prod corren como usuario `app` (uid 10001).
- Con `APP_ENV=production` o `DISABLE_API_DOCS=true` se desactivan `/docs`, `/redoc`, `/openapi.json`.

Detalle de secretos, TLS y variables: ver [server-hardening.md](./server-hardening.md).
