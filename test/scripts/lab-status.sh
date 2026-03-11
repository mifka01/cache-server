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

print_pid_line() {
  local key="$1"
  local pid="$2"
  if pid_matches_key "$key" "$pid"; then
    echo "${key}=${pid} alive"
  else
    echo "${key}=${pid} stale"
  fi
}

if [[ ! -f "$STATE_FILE" ]]; then
  echo "No lab session state found."
  echo "Start one with: nix run ./test#lab -- --servers 1 --clients 1"
  exit 0
fi

echo "state_dir=$STATE_DIR"
echo "status=$(state_value status)"
echo "servers=$(state_value servers)"
echo "clients=$(state_value clients)"

launcher_pid="$(state_value launcher_pid)"
if [[ -n "$launcher_pid" ]]; then
  print_pid_line "launcher_pid" "$launcher_pid"
fi

vde_pid="$(state_value vde_pid)"
if [[ -n "$vde_pid" ]]; then
  print_pid_line "vde_pid" "$vde_pid"
fi

echo "nodes:"
while IFS='=' read -r key value; do
  if [[ "$key" =~ ^(server|client)[0-9]+_ssh_port$ ]]; then
    node="${key%_ssh_port}"
    pid="$(state_value "${node}_pid")"
    if [[ -n "$pid" ]] && pid_matches_key "${node}_pid" "$pid"; then
      life="alive"
    else
      life="stale"
    fi
    echo "  ${node}: pid=${pid:-missing} (${life}) ssh_port=${value} log=${STATE_DIR}/${node}.log"
    echo "    attach: nix run ./test#lab-shell -- ${node}"
  fi
done < "$STATE_FILE"
