#!/bin/bash
# ============================================================================
# install.sh -- install daily-limits and its every-minute cache timer.
#
# Installs into the SYSTEM python's user site-packages (not a venv), because
# that is what the systemd user unit runs; earned-time and crdt-sync come in
# through the pinned git URLs in pyproject.toml (the pins the other consumers
# use). Then verifies the imports with that exact interpreter and enables the
# timer.
# Idempotent. `--dry-run` prints every step instead of running it.
# ============================================================================

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_DIR
readonly SYSTEM_PYTHON="/usr/bin/python3"
readonly UNIT_DIR="${HOME}/.config/systemd/user"
readonly BIN="${HOME}/.local/bin/daily-limits"
readonly UNITS=(daily-limits.service daily-limits.timer)
DRY_RUN=0

log() { printf 'install: %s\n' "$1" >&2; }
fail() {
    printf 'install: FAILED -- %s\n' "$1" >&2
    exit 1
}

# Run a command, or only print it under --dry-run.
run() {
    if ((DRY_RUN)); then
        printf '  would run: %s\n' "$*"
        return 0
    fi
    "$@"
}

usage() {
    echo "Usage: $(basename "$0") [--dry-run]"
    exit 0
}

install_package() {
    log "installing into the system python's user site-packages"
    # earned_time is shared with the root gaming daemon and screen-locker. If
    # it is already there, keep it: the URL pin would otherwise reinstall --
    # and, once the consumers are re-pinned to a newer tag, DOWNGRADE -- it.
    # crdt_sync is shared the same way (every Firebase app), so the same rule
    # covers both: --no-deps only when neither would be installed by the pins.
    local deps=()
    if "$SYSTEM_PYTHON" -c 'import earned_time, crdt_sync' 2>/dev/null; then
        log "earned_time and crdt_sync already installed; keeping them (--no-deps)"
        deps=(--no-deps)
    fi
    run "$SYSTEM_PYTHON" -m pip install --user --break-system-packages -q \
        "${deps[@]}" "$REPO_DIR" || fail "pip install"
}

verify_runtime() {
    log "verifying imports and the entry point"
    run "$SYSTEM_PYTHON" -c "import daily_limits._cli, earned_time, crdt_sync, tkinter" ||
        fail "a runtime dependency is missing from the system python"
    if ((!DRY_RUN)); then
        [[ -x "$BIN" ]] || fail "no entry point at $BIN"
    fi
    # A run that cannot write the cache is the timer's failure; catch it now.
    # (--sync exits 0 when only Firebase failed; that is a logged warning.)
    run "$BIN" --sync || fail "daily-limits --sync"
}

install_units() {
    log "installing systemd user units into $UNIT_DIR"
    run mkdir -p "$UNIT_DIR"
    local unit
    for unit in "${UNITS[@]}"; do
        run install -m 644 "$REPO_DIR/systemd/$unit" "$UNIT_DIR/"
    done
    run systemctl --user daemon-reload
    run systemctl --user enable --now daily-limits.timer
}

main() {
    install_package
    verify_runtime
    install_units
    log "done -- cache: \${XDG_RUNTIME_DIR}/daily-limits.json ; popup: daily-limits --gui"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -h | --help) usage ;;
        *) fail "unknown option: $1" ;;
    esac
done

main
