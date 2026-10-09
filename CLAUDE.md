# daily-limits -- notes for agents

Read README.md first, then DOCS-sources.md.

## Invariants

- **Read-only.** Never write the shutdown schedule, a ledger or the budget, and
  never talk to or restart steam-backlog-enforcer's daemon. The only write is
  the cache file under `$XDG_RUNTIME_DIR`.
- **No hard-coded minutes.** Every number comes from `earned_time` (`EARNERS`,
  `Earner` fields, `resolve()`, the ceiling constants). A registry bump must
  change the output with no code change here.
- **`None` is "could not check".** It renders as `unknown` / `[?]`, never as
  "not yet".
- **The JSON contract is frozen.** The i3blocks block parses it. Add keys only
  with that script.
- **Stdlib + earned_time only, and every earner is read generically** from its
  ledger (`_answers.py`). Never read another app's private files (nothing
  under `~/src/screen-locker`). An earner with no ledger is `unknown`.
- **Gaming is per gaming day** (06:00 boundary, `gaming.day`). Shutdown is per
  calendar day.
- Tests must redirect every `_paths` constant. They must never read the real
  ledgers, key, schedule or playtime state.

## Commands

- run: `PYTHONPATH=. python3 -m daily_limits`
- test: `.venv/bin/python -m pytest -q`
- test-changed: `scripts/test_changed.sh`
- lint: `ruff check . && .venv/bin/python -m mypy daily_limits`
- coverage: `.venv/bin/python -m pytest -q --cov-report=lcov:coverage.lcov`
- coverage-gaps: `coverage-gaps coverage.lcov`

Heavy commands go through `~/.claude/scripts/capped.sh`. Dev venv:
`scripts/setup_dev.sh`.
