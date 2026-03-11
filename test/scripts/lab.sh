#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
FLAKE_REF="${TEST_FLAKE_REF:-${TESTS_FLAKE_REF:-${QA_FLAKE_REF:-$ROOT_DIR/test}}}"
SERVERS=1
CLIENTS=1
OPEN_VIEWERS=0

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/cache-server-lab"
STATE_FILE="$STATE_DIR/state"
VDE_DIR="$STATE_DIR/vde1.ctl"
VDE_PID_FILE="$STATE_DIR/vde.pid"

set_state() {
  local key="$1"
  local value="$2"
  if [[ -f "$STATE_FILE" ]] && grep -q "^${key}=" "$STATE_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$STATE_FILE"
  else
    echo "${key}=${value}" >> "$STATE_FILE"
  fi
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
      cmdline_has "$pid" "vde_switch" && cmdline_has "$pid" "$VDE_DIR"
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --servers)
      SERVERS="$2"
      shift 2
      ;;
    --clients)
      CLIENTS="$2"
      shift 2
      ;;
    --open-viewers)
      OPEN_VIEWERS=1
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: nix run ./test#lab -- [--servers N] [--clients M] [--open-viewers]"
      exit 1
      ;;
  esac
done

if ! [[ "$SERVERS" =~ ^[1-5]$ ]] || ! [[ "$CLIENTS" =~ ^[1-5]$ ]]; then
  echo "--servers and --clients must be between 1 and 5"
  exit 1
fi

if [[ -f "$STATE_FILE" ]]; then
  echo "Lab already running. Stop it first with: nix run ./test#lab-stop"
  exit 1
fi

mkdir -p "$STATE_DIR"

DRIVER_DIR="$(nix build --no-link --print-out-paths "$FLAKE_REF#checks.x86_64-linux.lab-vm.driver")"
DRIVER_WRAPPER="$DRIVER_DIR/bin/nixos-test-driver"

START_SCRIPTS_RAW="$(sed -n "s/^export startScripts='\(.*\)'/\1/p" "$DRIVER_WRAPPER")"
if [[ -z "$START_SCRIPTS_RAW" ]]; then
  echo "Unable to read start scripts from driver wrapper"
  exit 1
fi

declare -A SCRIPT_BY_NODE
for script in $START_SCRIPTS_RAW; do
  base="$(basename "$script")"
  node="${base#run-}"
  node="${node%-vm}"
  SCRIPT_BY_NODE["$node"]="$script"
done

detect_vnc_viewer() {
  for bin in remote-viewer gvncviewer vinagre vncviewer xtigervncviewer; do
    if command -v "$bin" >/dev/null 2>&1; then
      echo "$bin"
      return 0
    fi
  done
  return 1
}

open_vnc_window() {
  local port="$1"
  local viewer
  viewer="$(detect_vnc_viewer || true)"
  if [[ -z "$viewer" ]]; then
    echo "[lab] No VNC viewer found. Connect manually to 127.0.0.1:${port}"
    return
  fi

  case "$viewer" in
    remote-viewer)
      "$viewer" --auto-resize=always --zoom="${QA_VNC_ZOOM:-125}" --title="lab-${port}" "vnc://127.0.0.1:${port}" >/dev/null 2>&1 &
      ;;
    gvncviewer|vinagre)
      "$viewer" "127.0.0.1:${port}" >/dev/null 2>&1 &
      ;;
    vncviewer|xtigervncviewer)
      "$viewer" -RemoteResize=1 -geometry "${QA_VNC_GEOMETRY:-1400x900}" "127.0.0.1:${port}" >/dev/null 2>&1 &
      ;;
  esac
}

cleanup() {
  if [[ -f "$STATE_FILE" ]]; then
    while IFS='=' read -r key value; do
      if [[ "$key" == *_pid ]] && [[ "$key" != "launcher_pid" ]]; then
        safe_kill_state_pid "$key" "$value"
      fi
    done < "$STATE_FILE"
  fi
  if [[ -n "${VDE_PID:-}" ]]; then
    safe_kill_state_pid "vde_pid" "$VDE_PID"
  fi
  rm -f "$STATE_FILE"
  rm -f "$VDE_PID_FILE"
  rm -rf "$VDE_DIR"
}

trap cleanup EXIT INT TERM

vde_switch --daemon --pidfile "$VDE_PID_FILE" --sock "$VDE_DIR" --dirmode 0700 --hub >/dev/null 2>&1

VDE_PID=""
if [[ -f "$VDE_PID_FILE" ]]; then
  VDE_PID="$(<"$VDE_PID_FILE")"
fi

for _ in $(seq 1 30); do
  if [[ -d "$VDE_DIR" ]]; then
    break
  fi
  sleep 1
done

if [[ ! -d "$VDE_DIR" ]]; then
  echo "[lab] Failed to initialize vde switch socket at $VDE_DIR"
  exit 1
fi

{
  echo "servers=$SERVERS"
  echo "clients=$CLIENTS"
  echo "status=starting"
  echo "vde_pid=${VDE_PID}"
  echo "launcher_pid=$$"
} > "$STATE_FILE"

launch_node() {
  local node="$1"
  local ssh_port="$2"
  local script="${SCRIPT_BY_NODE[$node]:-}"
  if [[ -z "$script" ]]; then
    echo "Missing start script for node: $node"
    exit 1
  fi

  local vm_state="$STATE_DIR/vm-state-$node"
  mkdir -p "$vm_state"
  local log_file="$STATE_DIR/$node.log"

  QEMU_VDE_SOCKET_1="$VDE_DIR" \
  QEMU_NET_OPTS="hostfwd=tcp::${ssh_port}-:22" \
  NIX_DISK_IMAGE="$vm_state/${node}.qcow2" \
  "$script" >"$log_file" 2>&1 &

  local pid=$!
  set_state "${node}_pid" "$pid"
  set_state "${node}_ssh_port" "$ssh_port"
}

echo "[lab] Starting lab with ${SERVERS} server(s) and ${CLIENTS} client(s)..."

for i in $(seq 1 "$SERVERS"); do
  launch_node "server${i}" "$((2200 + i))"
done

for i in $(seq 1 "$CLIENTS"); do
  launch_node "client${i}" "$((2300 + i))"
done

if [[ "$OPEN_VIEWERS" == "1" ]]; then
  for i in $(seq 0 "$((SERVERS + CLIENTS - 1))"); do
    open_vnc_window "$((5900 + i))"
  done
else
  echo "[lab] Viewer windows disabled (default)."
  echo "[lab] Use --open-viewers to auto-open VNC windows."
fi

wait_ssh() {
  local port="$1"
  for _ in $(seq 1 120); do
    if sshpass -p root ssh -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=1 -p "$port" root@127.0.0.1 true >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

for i in $(seq 1 "$SERVERS"); do
  echo "[lab] Waiting for server${i} SSH on localhost:$((2200 + i))..."
  wait_ssh "$((2200 + i))" || { echo "server${i} did not become reachable via ssh"; exit 1; }
done

for i in $(seq 1 "$CLIENTS"); do
  echo "[lab] Waiting for client${i} SSH on localhost:$((2300 + i))..."
  wait_ssh "$((2300 + i))" || { echo "client${i} did not become reachable via ssh"; exit 1; }
  echo "[lab] Running client setup on client${i}..."
  sshpass -p root ssh -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p "$((2300 + i))" root@127.0.0.1 'systemctl start cache-test-client-setup.service' >/dev/null
done

set_state "status" "ready"

echo "[lab] Ready. Attach with:"
for i in $(seq 1 "$CLIENTS"); do
  echo "  nix run ./test#lab-shell -- client${i}"
done
for i in $(seq 1 "$SERVERS"); do
  echo "  nix run ./test#lab-shell -- server${i}"
done
echo "[lab] Press Ctrl+C in this terminal to stop lab."

while true; do sleep 3600; done
