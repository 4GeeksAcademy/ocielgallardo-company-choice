#!/usr/bin/env bash
# Print evidence for HealthCore server baseline (SSH / non-root / UFW).
# Exit 0 when checks pass; non-zero when a required control is missing.
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-healthcore}"
HEALTHCORE_ROOT="${HEALTHCORE_ROOT:-/opt/healthcore}"
FAIL=0

pass() { echo "[PASS] $*"; }
fail() { echo "[FAIL] $*"; FAIL=1; }
info() { echo "[INFO] $*"; }

if [[ "$(uname -s)" != "Linux" ]]; then
  fail "Host is not Linux ($(uname -s)). Run verify on Codespaces/Ubuntu."
  echo "On Windows workstations: use Compose port lockdown as in-repo control;"
  echo "SSH/UFW evidence comes from a Linux VM or Codespaces run of this script."
  exit 1
fi

info "kernel=$(uname -r) user=$(id -un) euid=${EUID}"

if id -u "${DEPLOY_USER}" >/dev/null 2>&1; then
  pass "deploy user '${DEPLOY_USER}' exists"
else
  fail "deploy user '${DEPLOY_USER}' missing"
fi

if [[ "${EUID}" -eq 0 ]]; then
  info "verify running as root (acceptable for audit); daily ops should use ${DEPLOY_USER}"
else
  pass "verify running as non-root ($(id -un))"
fi

SSH_DROPIN="/etc/ssh/sshd_config.d/99-healthcore-hardening.conf"
if [[ -f "${SSH_DROPIN}" ]] && grep -Eq '^PermitRootLogin[[:space:]]+no' "${SSH_DROPIN}"; then
  pass "PermitRootLogin no (${SSH_DROPIN})"
else
  # Fallback: full sshd_config
  if grep -REq '^PermitRootLogin[[:space:]]+no' /etc/ssh/sshd_config /etc/ssh/sshd_config.d 2>/dev/null; then
    pass "PermitRootLogin no (sshd config)"
  else
    fail "PermitRootLogin no not found in sshd config"
  fi
fi

if command -v ufw >/dev/null 2>&1; then
  STATUS="$(ufw status 2>/dev/null || true)"
  if echo "${STATUS}" | grep -qi 'Status: active'; then
    pass "UFW is active"
  else
    fail "UFW is not active"
  fi
  echo "${STATUS}" | sed 's/^/       /'
  for port in 22 80 443; do
    if echo "${STATUS}" | grep -Eq "${port}/tcp"; then
      pass "UFW allows ${port}/tcp"
    else
      fail "UFW missing allow for ${port}/tcp"
    fi
  done
  for bad in 6379 6333 5555; do
    if echo "${STATUS}" | grep -Eq "${bad}/tcp"; then
      fail "UFW unexpectedly allows internal port ${bad}/tcp"
    else
      pass "UFW does not expose ${bad}/tcp"
    fi
  done
else
  fail "ufw not installed"
fi

echo "==> Folder permissions under ${HEALTHCORE_ROOT}"
check_dir_mode() {
  local path="$1"
  local expect="$2"
  local label="$3"
  if [[ ! -d "${path}" ]]; then
    fail "${label} missing (${path})"
    return
  fi
  local mode
  mode="$(stat -c '%a' "${path}" 2>/dev/null || stat -f '%OLp' "${path}" 2>/dev/null || echo "")"
  local owner
  owner="$(stat -c '%U' "${path}" 2>/dev/null || stat -f '%Su' "${path}" 2>/dev/null || echo "")"
  if [[ "${mode}" == "${expect}" ]]; then
    pass "${label} mode ${mode} (${path})"
  else
    fail "${label} expected mode ${expect}, got '${mode}' (${path})"
  fi
  if [[ "${owner}" == "${DEPLOY_USER}" ]]; then
    pass "${label} owner ${owner}"
  else
    fail "${label} expected owner ${DEPLOY_USER}, got '${owner}'"
  fi
}

check_dir_mode "${HEALTHCORE_ROOT}/app" "750" "app/"
check_dir_mode "${HEALTHCORE_ROOT}/logs" "750" "logs/"
check_dir_mode "${HEALTHCORE_ROOT}/secrets" "700" "secrets/"
check_dir_mode "${HEALTHCORE_ROOT}/config" "750" "config/"

if [[ "${FAIL}" -eq 0 ]]; then
  echo "==> All baseline checks passed."
  exit 0
fi
echo "==> Baseline checks failed (${FAIL})."
exit 1
