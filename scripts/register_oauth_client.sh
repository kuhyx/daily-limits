#!/bin/bash

# ============================================================================
# Walks the one step that cannot be automated -- registering the phone app's
# Android OAuth client -- and runs everything around it that can be.
#
# Why a human (or a browser) has to click: an OAuth client is a credential and
# Google exposes no create API for one. Neither gcloud nor the Firebase CLI
# has a command; the console is the only path.
#
# Until it exists, Google sign-in in com.kuhy.daily_limits fails with
# UNREGISTERED_ON_API_CONSOLE, which Credential Manager surfaces as the far
# less helpful "canceled: account reauth failed".
#
# What this does for you:
#   * derives the SHA-1 from the real release keystore (app/android/
#     key.properties), so the pasted value cannot be a stale copy;
#   * opens the console and puts each field on the clipboard in form order;
#   * verifies on the phone by reading the app's home screen back: "Not
#     signed in" until the keystore holds a Firebase session.
#
# Usage:
#   scripts/register_oauth_client.sh              # register, then verify
#   scripts/register_oauth_client.sh --sha1       # print the SHA-1 only
#   scripts/register_oauth_client.sh --verify-only
# ============================================================================

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_DIR
readonly CONSOLE_URL="https://console.cloud.google.com/auth/clients?project=kuhy-syncs"
readonly PACKAGE="com.kuhy.daily_limits"
readonly CLIENT_NAME="daily-limits"
readonly DEVICE="23181JEGR08034"
readonly DUMP=/tmp/daily_limits_ui.xml

log() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
step() { printf '   %s\n' "$1"; }

# Copies to the clipboard when a tool is available; prints regardless, so this
# still works over ssh with no X display.
clip() {
    if command -v xclip >/dev/null 2>&1; then
        printf '%s' "$1" | xclip -selection clipboard 2>/dev/null || true
        printf '   \033[32m[copied]\033[0m %s\n' "$1"
    else
        printf '   %s\n' "$1"
    fi
}

pause() { read -rp "   ...press Enter when that field is filled " _; }

# Reads one key out of key.properties.
prop() {
    grep -E "^$1=" "$2" | cut -d= -f2-
}

# Reads the release signing fingerprint out of the keystore itself.
release_sha1() {
    local properties="$REPO_DIR/app/android/key.properties"
    if [[ ! -f "$properties" ]]; then
        echo "error: $properties not found; cannot derive the SHA-1" >&2
        return 1
    fi
    local store password alias
    store="$(prop storeFile "$properties")"
    password="$(prop storePassword "$properties")"
    alias="$(prop keyAlias "$properties")"
    [[ "$store" = /* ]] || store="$REPO_DIR/app/android/$store"
    keytool -list -v -keystore "$store" -alias "$alias" \
        -storepass "$password" 2>/dev/null |
        grep -E '^[[:space:]]*SHA1:' | head -1 | sed 's/.*SHA1: //' | tr -d ' \r'
}

# Dumps the current screen so nodes can be found by their text.
dump_ui() {
    adb -s "$DEVICE" shell uiautomator dump /sdcard/dl_ui.xml >/dev/null 2>&1
    adb -s "$DEVICE" pull /sdcard/dl_ui.xml "$DUMP" >/dev/null 2>&1
}

has_text() { grep -q "text=\"[^\"]*$1" "$DUMP"; }

# Launches the app and reads its home screen, which asks the keystore for a
# session -- so a revoked one shows as signed out, not a stale local flag.
verify_on_phone() {
    log "Verifying on the phone"
    if ! adb devices | grep -q "^$DEVICE"; then
        step "phone not attached; reconnect it and rerun with --verify-only"
        return 1
    fi
    adb -s "$DEVICE" shell am start -n "$PACKAGE/.MainActivity" >/dev/null 2>&1
    sleep 6
    dump_ui
    if has_text "Not signed in"; then
        log "NOT SIGNED IN yet."
        step "Settings (top right) -> Sync settings -> 'Sign in with Google',"
        step "and pick the account the database rules pin (uid OvA2REQy...)."
        step "Then rerun: scripts/register_oauth_client.sh --verify-only"
        return 1
    fi
    if has_text "Published "; then
        log "SIGNED IN — the phone reads the PC's status."
        return 0
    fi
    log "Signed in, but no 'Published HH:MM' line on screen."
    step "Is daily-limits.service running on the PC? Screen dump: $DUMP"
    return 1
}

register() {
    local sha1
    sha1="$(release_sha1)"
    if [[ -z "$sha1" ]]; then
        echo "error: could not read a SHA-1 from the keystore" >&2
        exit 1
    fi

    log "Register ONE Android OAuth client in project kuhy-syncs"
    step "Google has no API for this. One form, three fields."
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$CONSOLE_URL" >/dev/null 2>&1 &
    else
        step "$CONSOLE_URL"
    fi
    sleep 2

    step "Click '+ CREATE CLIENT', set Application type = Android."
    step "Field 'Name':"
    clip "$CLIENT_NAME"
    pause
    step "Field 'Package name':"
    clip "$PACKAGE"
    pause
    step "Field 'SHA-1 certificate fingerprint':"
    clip "$sha1"
    pause
    step "Click CREATE. Do NOT touch the existing Web client: it is the"
    step "audience the app's tokens are minted for (kServerClientId)."
    read -rp "   Propagation takes a few minutes. Sign in on the phone, then Enter: " _
    verify_on_phone
}

main() {
    case "${1:-}" in
        --verify-only) verify_on_phone ;;
        --sha1) release_sha1 ;;
        "") register ;;
        *)
            echo "usage: $0 [--verify-only|--sha1]" >&2
            exit 2
            ;;
    esac
}

main "$@"
