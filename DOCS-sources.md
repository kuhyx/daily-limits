# Data sources and their caveats

Everything is read-only. The only file written is
`$XDG_RUNTIME_DIR/daily-limits.json`.

## The HMAC key (`/etc/workout-locker/hmac.key`)

- The key is `root:root 0644` **on purpose**. The gate timers (leetcode-guard,
  book-guard, anki-guard, ...) run as the user and sign their ledger rows with
  it, so the user must be able to read it.
- Because it is readable, this app can verify every row.
- If it were ever unreadable, `earned_time.read_key` would return `None` and
  every earner would read `unknown` (`[?] could not check`), never "not yet".

## Earners (`_answers.py`)

Every earner is read generically from its own signed ledger,
`~/<Earner.ledger>`:

- **Flat earners** use `earned_time.done_today`.
- **Counted earners** (the workout) use `earned_time.credit_units` when the
  installed earned_time has it. Otherwise `done_today` answers for the first
  unit only.
- **No ledger:** an earner the installed earned_time gives no ledger (the
  workout on 0.3.0) is `unknown`, with a warning logged on every run. It is
  never read from another app's private files.
- **Credit window:** each answer counts credits from midnight to `now` of the
  day asked about. For a past gaming day the window ends at that day's last
  second.

## Gaming (`playtime_state.json`)

- steam-backlog-enforcer's day runs 06:00 to 06:00. Before 06:00, `gaming.day`
  is yesterday's date. The budget is resolved for that day, and `used_minutes`
  is that day's `seconds`.
- If the state's `day_key` is older than the gaming day, nothing has been
  played yet: `0`.
- If `day_key` is newer than the gaming day (only possible with a faked
  clock), the value is `null` and a warning is logged.
- The enforcer holds `max(live, stored)` for the day. Its enforced budget can
  therefore exceed `budget_minutes` here after a mid-day registry cut.

## Applied shutdown (`/etc/shutdown-schedule.conf`)

- Keys are day ranges (`MON_WED_MINUTES`, `THU_SUN_MINUTES`). A single day
  (`FRI_MINUTES`) is also accepted.
- `MORNING_END_MINUTES` and the legacy `*_HOUR` keys are ignored.
- It can differ from the resolved time, for example on a sick day or before
  screen-locker's live pass runs. Both are shown.
