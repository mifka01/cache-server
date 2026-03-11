# Testing

- tests are written in `pytest`
- tests always run inside NixOS VMs

## Quick Start

Run all tests:

```bash
nix run ./test#pytest
```

Show full Nix/VM logs (build + boot + test driver):

```bash
QA_NIX_VERBOSE=1 nix run ./test#pytest
```

## Manual VM Lab

Start lab VMs

```bash
nix run ./test#lab -- --servers 3 --clients 2
```

Auto-open VNC viewer windows only when requested:

```bash
nix run ./test#lab -- --servers 3 --clients 2 --open-viewers
```

Defaults are `--servers 1 --clients 1` and viewer auto-open is off, so this also works:

```bash
nix run ./test#lab
```

Supported ranges:

- servers: 1-5
- clients: 1-5

Server node names are indexed: `server1`, `server2`, ... `serverN`.
Client names are indexed similarly: `client1`, `client2`, ... `clientM`.

The command keeps lab running until you press Ctrl+C in the launcher terminal.
You can also stop it from another terminal with `nix run ./test#lab-stop`.
Use `nix run ./test#lab-clean` to remove stale lab state, logs, and VM artifacts.

At ready state, `lab` prints all valid attach targets for the current topology.

## Test Directory Layout

- `test/tests/contracts/`
  - stable external API contract checks
- `test/tests/scenarios/`
  - end-to-end workflows (example: cachix push)
- `test/tests/nonfunctional/`
  - reserved for perf/load/resilience tests
- `test/tests/conftest.py`
  - shared fixtures and helpers


## Common Commands

- Run tests: `nix run ./test#pytest`
- Run verbose logs: `QA_NIX_VERBOSE=1 nix run ./test#pytest`
- Build check directly: `nix build ./test#blackbox-pytest-vm`
- Open manual VM lab: `nix run ./test#lab -- --servers 3 --clients 2`
- Open manual VM lab with viewers: `nix run ./test#lab -- --servers 3 --clients 2 --open-viewers`
- Attach shell in terminal: `nix run ./test#lab-shell -- client1`
- Show lab session health: `nix run ./test#lab-status`
- Show node logs: `nix run ./test#lab-logs -- --node server1`
- Stop running lab from another terminal: `nix run ./test#lab-stop`
- Remove stale lab artifacts: `nix run ./test#lab-clean`

## Troubleshooting

- If output looks too quiet, use verbose mode:
  - `QA_NIX_VERBOSE=1 nix run ./test#pytest`
- If a run fails before pytest starts, use:
  - `nix build ./test#blackbox-pytest-vm -L`
- If `lab-shell` says stale state or target not running, clean and restart:
  - `nix run ./test#lab-clean`
  - `nix run ./test#lab -- --servers 1 --clients 1`
