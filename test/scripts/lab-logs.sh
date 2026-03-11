#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/cache-server-lab"
NODE=""
LIST_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --node)
      NODE="$2"
      shift 2
      ;;
    --list)
      LIST_ONLY=1
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: nix run ./test#lab-logs -- [--node server1|client1] [--list]"
      exit 1
      ;;
  esac
done

if [[ ! -d "$STATE_DIR" ]]; then
  echo "No lab runtime directory found."
  exit 1
fi

if [[ "$LIST_ONLY" == "1" || -z "$NODE" ]]; then
  echo "Available logs in $STATE_DIR:"
  found=0
  for log_file in "$STATE_DIR"/*.log; do
    if [[ -f "$log_file" ]]; then
      found=1
      base="$(basename "$log_file")"
      echo "  ${base%.log}"
    fi
  done
  if [[ "$found" == "0" ]]; then
    echo "  (none)"
  fi
  if [[ -z "$NODE" ]]; then
    echo "Use: nix run ./test#lab-logs -- --node server1"
    exit 0
  fi
fi

if [[ ! "$NODE" =~ ^(server|client)[0-9]+$ ]]; then
  echo "Invalid node '$NODE'. Use serverN or clientN."
  exit 1
fi

LOG_FILE="$STATE_DIR/${NODE}.log"
if [[ ! -f "$LOG_FILE" ]]; then
  echo "Log file not found: $LOG_FILE"
  exit 1
fi

echo "--- $LOG_FILE ---"
cat "$LOG_FILE"
