#!/usr/bin/env bash
# HealthCore academic baseline: non-root deploy user, SSH, UFW.
# Target: Ubuntu/Debian or GitHub Codespaces (Linux). Idempotent.
# Do NOT run on Windows hosts — use Codespaces/Ubuntu for evidence.
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-healthcore}"
HEALTHCORE_ROOT="${HEALTHCORE_ROOT:-/opt/healthcore}"
SSH_CONFIG="${SSH_CONFIG:-/etc/ssh/sshd_config}"
SSH_DROPIN_DIR="${SSH_DROPIN_DIR:-/etc/ssh/sshd_config.d}"
UFW_BIN="${UFW_BIN:-ufw}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: This script only runs on Linux (got $(uname -s))." >&2
  exit 1
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: Run as root (sudo)." >&2
  exit 1
fi

echo "==> Ensuring deploy user '${DEPLOY_USER}' (no root login for daily ops)"
if ! id -u "${DEPLOY_USER}" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "${DEPLOY_USER}"
fi
usermod -aG sudo "${DEPLOY_USER}" 2>/dev/null || usermod -aG wheel "${DEPLOY_USER}" 2>/dev/null || true

# Lock down home permissions (no world-writable)
chmod 750 "/home/${DEPLOY_USER}" 2>/dev/null || true

echo "==> Folder layout under ${HEALTHCORE_ROOT} (code / logs / secrets)"
# Separate code, logs, and sensitive config with explicit modes.
#   app/     — application checkout / deploy tree (750)
#   logs/    — runtime logs (750)
#   secrets/ — .env, PEM, auth stores (700 — owner-only)
#   config/  — non-secret config templates (750)
mkdir -p \
  "${HEALTHCORE_ROOT}/app" \
  "${HEALTHCORE_ROOT}/logs" \
  "${HEALTHCORE_ROOT}/secrets" \
  "${HEALTHCORE_ROOT}/config"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${HEALTHCORE_ROOT}"
chmod 750 "${HEALTHCORE_ROOT}"
chmod 750 "${HEALTHCORE_ROOT}/app"
chmod 750 "${HEALTHCORE_ROOT}/logs"
chmod 700 "${HEALTHCORE_ROOT}/secrets"
chmod 750 "${HEALTHCORE_ROOT}/config"
# Drop a reminder file (no secrets) for operators.
cat >"${HEALTHCORE_ROOT}/README.perms.txt" <<EOF
HealthCore folder separation (Hito 29)
- app/      code         mode 750  owner ${DEPLOY_USER}
- logs/     logs         mode 750  owner ${DEPLOY_USER}
- secrets/  .env, PEM    mode 700  owner ${DEPLOY_USER}
- config/   non-secret   mode 750  owner ${DEPLOY_USER}
Map Compose: mount/copy repo into app/; keep host .env and data/process/auth/ under secrets/.
EOF
chown "${DEPLOY_USER}:${DEPLOY_USER}" "${HEALTHCORE_ROOT}/README.perms.txt"
chmod 640 "${HEALTHCORE_ROOT}/README.perms.txt"

echo "==> SSH: PermitRootLogin no, PasswordAuthentication no (key-only)"
mkdir -p "${SSH_DROPIN_DIR}"
DROPIN="${SSH_DROPIN_DIR}/99-healthcore-hardening.conf"
cat >"${DROPIN}" <<'EOF'
# Managed by scripts/hardening/harden-linux-baseline.sh (HealthCore Hito 29)
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
ChallengeResponseAuthentication no
EOF

if command -v systemctl >/dev/null 2>&1; then
  systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null || true
fi

echo "==> UFW: default deny incoming; allow 22, 80, 443 only"
if ! command -v "${UFW_BIN}" >/dev/null 2>&1; then
  echo "WARNING: ufw not installed; install with: apt-get install -y ufw" >&2
else
  "${UFW_BIN}" --force reset >/dev/null
  "${UFW_BIN}" default deny incoming
  "${UFW_BIN}" default allow outgoing
  "${UFW_BIN}" allow 22/tcp comment 'SSH'
  "${UFW_BIN}" allow 80/tcp comment 'HTTP'
  "${UFW_BIN}" allow 443/tcp comment 'HTTPS'
  # Lab APIs stay behind compose network / reverse proxy — not opened on host UFW.
  "${UFW_BIN}" --force enable
  "${UFW_BIN}" status verbose
fi

echo "==> Baseline hardening applied."
echo "Verify with: sudo bash scripts/hardening/verify-baseline.sh"
