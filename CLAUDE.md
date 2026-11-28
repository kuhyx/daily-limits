# daily-limits -- notes for agents

Read README.md first, then DOCS-sources.md.

## Invariants

- **Read-only locally.** Never write the shutdown schedule, a ledger or the
  budget, and never talk to or restart steam-backlog-enforcer's daemon. Local
  writes: the cache under `$XDG_RUNTIME_DIR`, `--sync`'s state under
  `~/.local/share/daily-limits/` and the shadow alerts' state under
  `~/.local/state/daily-limits/`. Remote writes: only `daily_limits-e2e/`
  in Firebase, sealed, never plaintext (README "Firebase"). The popup's one button may *launch* the
  sickdays picker (`_sick_picker.py`: `sickdays gui`, detached, a subprocess,
  never an import); that program owns its own writes. Two rows open their work
  the same way: `focus` (`_focus_open.py`: `focus_project.open`) and `leetcode`
  (`_leetcode_open.py`: `leetcode_guard.open_cli`, the first suggested problem
  in the browser; its exit status is read, so a failed open shows the warning).
- **The shadow week only shows.** `_alerts` may run `notify-send` and launch
  the splash through `systemd-run --user` (unit `daily-limits-shadow-splash`);
  the splash is override-redirect and must never grab or take focus. Its
  numbers are the enforcer's C4 fields only (`_shadow.py`).
- **A rest day goes through screen-locker's own CLI** (`_rest_day.py`, a
  subprocess), never an import, and only with a strictly validated date.
- **The app is offline first.** It shows the cached status before any
  network call, and every request is saved locally first (`newRequest`,
  `SentRequest.isQueued`) and uploaded by the next sync pass that can reach
  Firebase (`uploadQueued`, app or background task).
- **Firebase never breaks the cache.** The cache is written first; any sync
  failure is one warning and exit 0.
- **A top-up is never a to-do.** An earner with `Earner.topup` (the LeetCode
  review, earned_time 0.23.0) is listed only on a day it was credited and
  never appears in `todo` (`_report._shown`): a bonus nobody owed is not a
  missed task. Key on the property, never on the name.
- **No hard-coded minutes.** Every number comes from `earned_time` (`EARNERS`,
  `Earner` fields, `resolve()`, the ceiling constants). A registry bump must
  change the output with no code change here.
- **`None` is "could not check".** It renders as `unknown` / `[?]`, never as
  "not yet".
- **Sick days come from `sickdays.is_sick_day(day)`** for the day being
  resolved (the calendar day for shutdown, the gaming day for the gaming
  resolve); never today's answer for another day. Tests redirect its pool
  (`sick_pool` fixture).
- **The JSON contract is frozen.** The i3blocks block parses it. Add keys only
  with that script.
- **Stdlib + earned_time + sickdays + crdt_sync only, and every earner is read generically** from its
  ledger (`_answers.py`). Never read another app's private files (nothing
  under `~/src/screen-locker`). An earner with no ledger is `unknown`.
- **Phase 2 is asked, never read.** `leisure_active` comes only from
  `earned_time.leisure_active(gaming_day, path=_paths.LEISURE_FROM_FILE)`;
  nothing here opens the switch file. Tests point it (and earned_time's own
  `LEISURE_FROM_PATH`) at a missing temp file; `leisure_on` writes it.
- **No gaming budget from 2026-11-16.** `gaming_enforced` (the gaming day's
  `earned_time.gaming_enforced`) false: render nothing gaming/leisure, anywhere.
- **Gaming is per gaming day** (06:00 boundary, `gaming.day`). Shutdown is per
  calendar day.
- Tests must redirect every `_paths` constant. They must never read the real
  ledgers, key, schedule or playtime state, nor touch Firebase, nor read the
  real crdt-sync passphrase (conftest points `_paths.PASSWORD_FILE` at a temp file).

## Commands

- run: `PYTHONPATH=. python3 -m daily_limits`
- deploy: `scripts/deploy.sh`
- test: `.venv/bin/python -m pytest -q`
- test-changed: `scripts/test_changed.sh`
- lint: n/a: dropped (kuhy, 2026-11-27)
- coverage: n/a: dropped (kuhy, 2026-11-27)
- coverage-gaps: n/a: dropped (kuhy, 2026-11-27)
- app (Flutter, `app/`; fvm SDK first, see `app/README.md`):
  `cd app && PATH=~/sdk/fvm/versions/3.50.0/bin:$PATH flutter analyze --fatal-infos && flutter test -j 1 --coverage`

Heavy commands go through `~/.claude/scripts/capped.sh`. Dev venv:
`scripts/setup_dev.sh`.
