#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-client1}"
STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/cache-server-lab"
STATE_FILE="$STATE_DIR/state"
WAIT_SECONDS="${TEST_LAB_WAIT_SECONDS:-${TESTS_LAB_WAIT_SECONDS:-${QA_LAB_WAIT_SECONDS:-120}}}"

state_value() {
  local key="$1"
  grep -E "^${key}=" "$STATE_FILE" | cut -d= -f2- || true
}

pid_is_alive() {
  local pid="$1"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1
}

cmdline_has() {
  local pid="$1"
  local needle="$2"
  [[ -r "/proc/$pid/cmdline" ]] || return 1
  grep -aq -- "$needle" "/proc/$pid/cmdline"
}

pid_matches_key() {
  local key="$1"
  local pid="$2"
  local node
  pid_is_alive "$pid" || return 1

  case "$key" in
    launcher_pid)
      cmdline_has "$pid" "/bin/lab"
      ;;
    server[0-9]_pid|client[0-9]_pid)
      node="${key%_pid}"
      cmdline_has "$pid" "run-${node}-vm" || {
        cmdline_has "$pid" "qemu-system" && cmdline_has "$pid" "vm-state-${node}/${node}.qcow2"
      }
      ;;
    *)
      return 1
      ;;
  esac
}

is_session_alive() {
  local launcher_pid
  launcher_pid="$(state_value launcher_pid)"
  if [[ -n "$launcher_pid" ]] && pid_matches_key "launcher_pid" "$launcher_pid"; then
    return 0
  fi

  while IFS='=' read -r key value; do
    if [[ "$key" =~ ^(server|client)[0-9]+_pid$ ]] && pid_matches_key "$key" "$value"; then
      return 0
    fi
  done < "$STATE_FILE"
  return 1
}

if [[ ! -f "$STATE_FILE" ]]; then
  echo "No running lab session found. Start it first with:"
  echo "  nix run ./test#lab -- --servers 1 --clients 1"
  exit 1
fi

if ! is_session_alive; then
  echo "Lab state file exists but processes are not running (stale state)."
  echo "Clean it up with: nix run ./test#lab-stop"
  exit 1
fi

STATUS="$(state_value status)"
if [[ "$STATUS" != "ready" ]]; then
  for _ in $(seq 1 "$WAIT_SECONDS"); do
    STATUS="$(state_value status)"
    if [[ "$STATUS" == "ready" ]]; then
      break
    fi
    sleep 1
  done
fi

if [[ "$STATUS" != "ready" ]]; then
  echo "Lab is still starting (status=${STATUS:-unknown})."
  echo "Try again in a moment, or check logs in $STATE_DIR"
  exit 1
fi

PORT="$(state_value "${TARGET}_ssh_port")"
if [[ -z "$PORT" ]]; then
  echo "Unknown target '${TARGET}' in current lab session."
  echo "Available targets:"
  grep -E '^(server|client)[0-9]+_ssh_port=' "$STATE_FILE" | sed 's/_ssh_port=.*//' | sort
  exit 1
fi

NODE_PID="$(state_value "${TARGET}_pid")"
if [[ -z "$NODE_PID" ]] || ! pid_matches_key "${TARGET}_pid" "$NODE_PID"; then
  echo "Target '${TARGET}' is not running."
  echo "Check logs: $STATE_DIR/${TARGET}.log"
  exit 1
fi

for _ in $(seq 1 "$WAIT_SECONDS"); do
  if sshpass -p root ssh -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=1 -p "$PORT" root@127.0.0.1 true >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! sshpass -p root ssh -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=1 -p "$PORT" root@127.0.0.1 true >/dev/null 2>&1; then
  echo "Target '${TARGET}' is running but SSH on localhost:${PORT} is not ready yet."
  echo "Check logs: $STATE_DIR/${TARGET}.log"
  exit 1
fi

echo "[lab-shell] Attaching to ${TARGET} on localhost:${PORT}"
exec sshpass -p root ssh -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p "$PORT" root@127.0.0.1
