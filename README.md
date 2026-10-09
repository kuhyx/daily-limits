# daily-limits

What is my shutdown time and gaming limit today, and what do I still need to do
to extend them?

A desktop status app over [`earned_time`](https://github.com/kuhyx/utils/tree/main/earned_time),
the one registry of what every gate (workout, LeetCode, reading, Anki,
Automation) earns. It never writes the schedule or the budget. The
consumers (screen-locker, steam-backlog-enforcer) do that. It reports, and
publishes the report to Firebase for the phone app (`--sync`, below).

## Usage

```console
daily-limits                # human summary
daily-limits --json         # the JSON contract (below)
daily-limits --write-cache  # same JSON, atomically, to $XDG_RUNTIME_DIR/daily-limits.json
daily-limits --sync         # --write-cache, then the Firebase tick (below)
daily-limits --gui          # small Tk popup (Esc / q closes; refreshes every minute)
```

`install.sh` installs the package into the system python's user site-packages
and enables `daily-limits.timer` (every 60 s: `--sync`; the cache it writes
first is read by the i3blocks block). `install.sh --dry-run` prints every step instead.

## JSON contract

Fixed: the i3blocks block parses it.

```json
{"date": "YYYY-MM-DD", "generated_at": 1791532875,
 "shutdown": {"applied": "HH:MM|null", "resolved": "HH:MM", "floor": "HH:MM", "ceiling": "HH:MM"},
 "gaming": {"day": "YYYY-MM-DD", "budget_minutes": 180, "used_minutes": 94, "ceiling_minutes": 480},
 "earners": [{"name": "workout", "label": "workout", "status": "done|todo|unknown",
              "shutdown_minutes": 120, "gaming_minutes": 120}],
 "todo": [{"name": "workout", "label": "workout", "status": "todo|unknown", "shutdown_after": "20:00"}]}
```

- `shutdown.resolved` / `floor` / `ceiling` and `gaming.budget_minutes` come
  from `earned_time.resolve()` and its constants. Nothing is hard-coded.
  Per-earner `shutdown_minutes`, the ceiling and `todo` use the day-aware
  `shutdown_minutes_for` / `shutdown_ceiling_for` when the installed
  earned_time has them (the 2026-10-10 ladder), else the 0.3.0 fields
  (`_compat.py`).
- `shutdown.applied` is what screen-locker actually wrote to
  `/etc/shutdown-schedule.conf` (today's weekday `*_MINUTES` key). It can
  differ from `resolved` (sick day, a pending live pass); `null` if unreadable.
- `gaming` describes the enforcer's **gaming day** (06:00 to 06:00), named in
  `gaming.day`. Before 06:00 that is yesterday, so the budget is resolved for
  that day and matches `used_minutes`. Shutdown stays on the calendar `date`.
- `gaming.used_minutes` is from steam-backlog-enforcer's world-readable
  `~/.config/steam_backlog_enforcer/playtime_state.json`; `null` if unreadable.
- `status: "unknown"` means *could not check* (unreadable key or ledger). It is
  never a "no".
- `todo` lists the not-done earners in registry order, each with the cumulative
  shutdown time reached once it is done too (capped at the ceiling). Its
  `status` is `todo` or `unknown`, so a bar can show unknown ones as such.

## Where each status comes from

| earner | source |
|---|---|
| flat earners | `earned_time.done_today(earner, ~/<earner.ledger>, /etc/workout-locker/hmac.key)` |
| counted (workout) | `earned_time.credit_units(...)` on its ledger; `unknown` while the installed earned_time gives it no ledger (0.3.0) |

See `DOCS-sources.md` for the details and the known divergences.

## Firebase (`--sync`)

Through `crdt_sync.firebase_client_for("daily_limits")` (session cached in
`~/.config/daily_limits/firebase_auth.json`). Logical paths; on the wire every
`.` in a key is escaped (`status.json` is stored as `status~2Ejson`) and every
value is a JSON **string** holding the serialized document:

- `daily_limits/status.json` (PC writes): the contract above plus
  `published_at` (unix int) and `device_id` (this install's uuid,
  `~/.local/share/daily-limits/.device_id`). Written when the content changes
  (ignoring `generated_at`) and at least every 10 min.
- `daily_limits/requests/<id>.json` (phone writes): `{"id", "kind":
  "refresh"|"rest_day", "date": "YYYY-MM-DD"|null, "created_at", "device_id"}`.
- `daily_limits/results/<id>.json` (PC writes): `{"id", "ok", "message",
  "handled_at"}`; `<id>` is the request's filename. Deleted after 7 days.

Each request is answered once (`~/.local/share/daily-limits/handled_requests.json`),
then deleted. Older than 10 min: `ok=false, "expired"`. `refresh` republishes.
`rest_day` runs `/usr/bin/python3 -m screen_locker.screen_lock
--declare-rest-day <date>` (screen-locker applies every rule) and republishes.
A Firebase failure is one warning; the cache is written before any network call.

The phone side (status, widget, notifications, the two requests) is the
Flutter app in `app/`; see [`app/README.md`](app/README.md).
