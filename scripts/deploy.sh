#!/bin/bash
# ============================================================================
# deploy.sh -- deploy daily-limits for real: the desktop first, then the phone.
#
# Ship runs this (the CLAUDE.md `- deploy:` line). Both halves deploy the same
# commit: the live checkout ~/src/daily-limits, fast-forwarded to origin/main.
#
#   1. Preflight: the live checkout must be on main, clean, and fast-forward;
#      anything else exits 10 before a single thing changes.
#   2. Desktop: its install.sh, restart the timer and the focus path, run
#      daily-limits.service once. Health: both units active, the run exits 0
#      and rewrote the i3blocks cache with valid JSON. Failure exits 20.
#   3. Phone: release build through phone_deploy.sh's stages (`adb install -r`
#      only; app data is never wiped), then health: the app runs and has no
#      crash since. Phone unreachable exits 30, after the desktop passed;
#      health failure exits 50. phone_deploy.sh's own codes pass through.
#
# Idempotent: after a passing phone deploy a stamp records HEAD + the
# installed versionCode; a rerun with both unchanged skips the build and the
# install but still runs both health checks. (phone_deploy.sh owns the build
# number and takes no --build-name, so the stamp stands in for one.)
#
# Usage: deploy.sh [all|desktop|phone]     (default: all)
# Env:   DAILY_LIMITS_LIVE (default ~/src/daily-limits), ADB_SERIAL
# ============================================================================

set -euo pipefail

readonly LIVE="${DAILY_LIMITS_LIVE:-$HOME/src/daily-limits}"
readonly SERIAL="${ADB_SERIAL:-23181JEGR08034}"
readonly PKG="com.kuhy.daily_limits"
readonly SCRIPTS="$HOME/.claude/scripts"
readonly STAMP="$HOME/.cache/daily-limits-deploy/phone.stamp"
readonly CACHE="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/daily-limits.json"
readonly UNITS=(daily-limits.timer daily-limits-focus.path)
readonly LAUNCH_SETTLE_SECS="${DEPLOY_SETTLE_SECS:-3}"
HEAD=""

log() { printf 'deploy: %s\n' "$1" >&2; }
fail() {
    printf 'deploy: FAILED -- %s\n' "$2" >&2
    exit "$1"
}

usage() {
    sed -n '3,25p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
}

# --- 1. preflight ----------------------------------------------------------

preflight() {
    [[ -d $LIVE ]] || fail 10 "no live checkout at $LIVE"
    local branch
    branch=$(git -C "$LIVE" rev-parse --abbrev-ref HEAD)
    [[ $branch == main ]] || fail 10 "$LIVE is on '$branch', not main"
    [[ -z $(git -C "$LIVE" status --porcelain) ]] || fail 10 "$LIVE has local changes"
    git -C "$LIVE" pull --ff-only -q || fail 10 "$LIVE cannot fast-forward to origin/main"
    HEAD=$(git -C "$LIVE" rev-parse --short HEAD)
    log "live checkout at $HEAD"
}

# --- 2. desktop ------------------------------------------------------------

deploy_desktop() {
    log "desktop: install.sh"
    "$LIVE/install.sh" || fail 20 "install.sh"
    systemctl --user restart "${UNITS[@]}" || fail 20 "restart ${UNITS[*]}"

    # One oneshot run after the install: it runs the new code end to end.
    local started
    printf -v started '%(%s)T' -1
    systemctl --user start daily-limits.service || fail 20 "daily-limits.service run failed"

    local unit
    for unit in "${UNITS[@]}"; do
        systemctl --user is-active --quiet "$unit" || fail 20 "$unit is not active"
    done
    [[ -f $CACHE ]] || fail 20 "no cache at $CACHE"
    (($(stat -c %Y "$CACHE") >= started)) || fail 20 "cache $CACHE was not rewritten by this run"
    python3 -m json.tool "$CACHE" >/dev/null || fail 20 "cache $CACHE is not valid JSON"
    log "desktop: healthy (${UNITS[*]} active, cache fresh)"
}

# --- 3. phone --------------------------------------------------------------

phone_adb() { adb -s "$SERIAL" "$@"; }

installed_version_code() {
    phone_adb shell dumpsys package "$PKG" | tr -d '\r' |
        grep -o 'versionCode=[0-9]*' | head -1 | cut -d= -f2
}

# The staged build keeps each gradle call on phone_deploy's warm daemon; the
# Dart AOT stage is the memory-heavy one, hence the 4 GiB cap.
build_and_install() {
    local deploy="$SCRIPTS/phone_deploy.sh" capped="$SCRIPTS/capped.sh" stage
    ADB_SERIAL="$SERIAL" "$deploy" "$LIVE/app" --release --stage prep
    for stage in dart kotlin assemble; do
        ADB_SERIAL="$SERIAL" CAP_MEM=4G "$capped" "$deploy" "$LIVE/app" --stage "$stage"
    done
    ADB_SERIAL="$SERIAL" "$deploy" "$LIVE/app" --stage install
}

# No crash of the app in the device's crash buffer since `since` (device epoch).
check_no_crash() {
    local since="$1"
    if phone_adb logcat -b crash -d -T "$since.000" | tr -d '\r' | grep -q "Process: $PKG"; then
        fail 50 "$PKG crashed since $(date -d "@$since" '+%F %T')"
    fi
}

deploy_phone() {
    [[ $(phone_adb get-state 2>/dev/null | tr -d '\r') == device ]] ||
        fail 30 "phone $SERIAL is missing (desktop is deployed; plug it in and rerun, a rerun is safe)"

    local code stamp_head="" stamp_code="" stamp_since=""
    code=$(installed_version_code)
    if [[ -f $STAMP ]]; then
        read -r stamp_head stamp_code stamp_since <"$STAMP" || true
    fi
    if [[ -n $code && $stamp_head == "$HEAD" && $stamp_code == "$code" ]]; then
        log "phone: $HEAD already installed (versionCode $code); health check only"
        check_no_crash "$stamp_since"
        log "phone: healthy"
        return 0
    fi

    local since
    since=$(phone_adb shell date +%s | tr -d '\r')
    log "phone: building $HEAD (installed versionCode ${code:-none})"
    build_and_install
    sleep "$LAUNCH_SETTLE_SECS"

    [[ -n $(phone_adb shell pidof "$PKG" | tr -d '\r') ]] || fail 50 "$PKG is not running after launch"
    check_no_crash "$since"
    code=$(installed_version_code)
    [[ -n $code ]] || fail 50 "$PKG is not installed after the install step"
    mkdir -p "$(dirname "$STAMP")"
    printf '%s %s %s\n' "$HEAD" "$code" "$since" >"$STAMP"
    log "phone: healthy ($PKG running, versionCode $code)"
}

main() {
    local target="${1:-all}"
    case "$target" in
        all | desktop | phone) ;;
        -h | --help) usage ;;
        *) fail 2 "unknown target: $target (all|desktop|phone)" ;;
    esac
    preflight
    [[ $target == phone ]] || deploy_desktop
    [[ $target == desktop ]] || deploy_phone
    log "done ($target at $HEAD)"
}

main "$@"
