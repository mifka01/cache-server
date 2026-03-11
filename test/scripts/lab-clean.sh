#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/cache-server-lab"
STATE_FILE="$STATE_DIR/state"

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
    vde_pid)
      cmdline_has "$pid" "vde_switch" && cmdline_has "$pid" "$STATE_DIR/vde1.ctl"
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

safe_kill_state_pid() {
  local key="$1"
  local pid="$2"
  if pid_matches_key "$key" "$pid"; then
    kill "$pid" >/dev/null 2>&1 || true
  fi
}

if [[ -f "$STATE_FILE" ]]; then
  while IFS='=' read -r key value; do
    if [[ "$key" == *_pid ]]; then
      safe_kill_state_pid "$key" "$value"
    fi
  done < "$STATE_FILE"

  launcher_pid="$(state_value launcher_pid)"
  if [[ -n "$launcher_pid" ]]; then
    safe_kill_state_pid "launcher_pid" "$launcher_pid"
  fi
fi

rm -f "$STATE_FILE" "$STATE_DIR/vde.pid"
rm -rf "$STATE_DIR/vde1.ctl" "$STATE_DIR"/vm-state-* "$STATE_DIR"/*.log
echo "Lab state, logs, and VM artifacts cleaned."
