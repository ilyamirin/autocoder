#!/bin/sh
set -eu

DATA_DIR="${GITEA_RUNNER_DATA_DIR:-/data}"
STATE_FILE="${DATA_DIR}/.runner"
META_FILE="${DATA_DIR}/.runner-meta"
DESIRED_URL="${GITEA_INSTANCE_URL:-}"
DESIRED_REGISTRATION_TOKEN="${GITEA_RUNNER_REGISTRATION_TOKEN:-}"
FORCE_REREGISTER="${GITEA_RUNNER_FORCE_REREGISTER:-false}"

mkdir -p "${DATA_DIR}"

current_state_url=""
if [ -f "${STATE_FILE}" ]; then
  current_state_url="$(sed -n 's/.*"address": "\([^"]*\)".*/\1/p' "${STATE_FILE}" | head -n 1)"
fi

stored_meta_url=""
stored_meta_token=""
if [ -f "${META_FILE}" ]; then
  stored_meta_url="$(sed -n 's/^INSTANCE_URL=//p' "${META_FILE}" | head -n 1)"
  stored_meta_token="$(sed -n 's/^REGISTRATION_TOKEN=//p' "${META_FILE}" | head -n 1)"
fi

reset_reason=""
if [ "${FORCE_REREGISTER}" = "true" ]; then
  reset_reason="forced re-registration requested"
elif [ -n "${current_state_url}" ] && [ "${current_state_url}" != "${DESIRED_URL}" ]; then
  reset_reason="runner state URL changed"
elif [ -n "${stored_meta_url}" ] && [ "${stored_meta_url}" != "${DESIRED_URL}" ]; then
  reset_reason="stored instance URL changed"
elif [ -n "${stored_meta_token}" ] && [ "${stored_meta_token}" != "${DESIRED_REGISTRATION_TOKEN}" ]; then
  reset_reason="registration token changed"
fi

if [ -n "${reset_reason}" ]; then
  echo "Resetting runner state: ${reset_reason}"
  rm -f "${STATE_FILE}"
fi

cat > "${META_FILE}" <<EOF
INSTANCE_URL=${DESIRED_URL}
REGISTRATION_TOKEN=${DESIRED_REGISTRATION_TOKEN}
EOF

exec /usr/local/bin/run.sh
