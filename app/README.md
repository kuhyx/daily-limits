# daily_limits (phone app)

Today's shutdown time and gaming budget on the phone, as published by the PC
(`daily-limits --sync`), plus two requests the PC acts on: "Refresh now" and
"Declare rest day" (tomorrow up to a year ahead). The PC enforces; the phone
only displays and asks. `com.kuhy.daily_limits`, Flutter 3.47.7 (`.fvmrc`),
exact pins, Firebase RTDB only via crdt_sync_flutter (`kuhy-syncs`), no GitHub
mirror.

- Status screen, greyed with "PC offline since HH:MM" once `published_at` is
  older than 15 min.
- Home-screen widget: one line like the PC bar (`🔌 20:00 · 🎮 1h29 left ·
  +💪 +🧩`). A 15-min WorkManager job runs the app's sync pass in background.
- Local notifications only (no FCM): shutdown −30 / −10 min (exact alarms),
  gaming "10 min left" once per gaming day, the rest-day answer.

## Firebase contract

Paths and request/result shapes: root [README "Firebase"](../README.md#firebase---sync).
Timing: the PC publishes `status.json` on change and at least every 10 min. The
phone writes `requests/<uuid>.json` (`id` = that uuid; a request written as an
object rather than a JSON string is answered as malformed), polls
`results/<uuid>.json` every 5 s for 3 min, then shows "no answer yet (PC may be
off)" and re-enables the button. It keeps reading the result of every
unanswered request on the 1-min status pass and every background run until an
answer arrives (which replaces the line, and notifies for a rest day) or the
request is pruned after 2 days. The PC answers every request it sees -- up to
10 min old it acts or refuses, older ones get `expired` -- and keeps results 7
days. The phone never deletes anything.

## Layout (`lib/`)

- `main.dart`: the app.
- `main_preview.dart`: fixture layout preview (fresh, offline, widget line). No
  Firebase, notifications or cache.
- `main_probe.dart`: the real app plus one rest-day request for *yesterday*.
  The PC refuses it: a full refused round trip (card + notification) without
  writing a rest day.
- `main_probe_shutdown.dart`: schedules the real warnings for a fixture
  shutdown 11 min away, so the −10 min warning fires ~1 min after launch via
  the real `zonedSchedule` → exact-alarm path. Redeploy the normal build after;
  its first pass re-arms the real alarms.
- `model/status.dart`: strict `status.json` parser; `kOfflineAfter`.
- `services/sync_app.dart`: Firebase app, logical paths, `GoogleSignInBackend`.
- `services/requests.dart`: request/result documents; `kAnswerTimeout`.
- `services/local_cache.dart`: JSON file shared by the UI and WorkManager
  isolates (status, sent requests, one-shot notification flags).
- `services/sync_once.dart`: one pass: status, answers, cache, widget,
  notifications.
- `services/limits_controller.dart`: UI state, the two actions, answer polling.
- `services/notifier.dart`, `home_widget_sync.dart`, `background.dart`:
  notifications, the widget line (`DailyLimitsWidget.kt` only renders it), the
  15-min task.
- `screens/`: home, status view, actions card, settings (shared
  sync_settings_ui sign-in, widget, test notification).
- `ui/earner_icons.dart`: the PC bar's icons.

## Build and deploy

The system `flutter` is older than `.fvmrc` and `phone_deploy.sh` ignores
`.fvmrc`, so put the fvm SDK first:

```console
PATH=~/sdk/fvm/versions/3.47.7/bin:$PATH bash ~/.claude/scripts/phone_deploy.sh \
  ~/src/daily-limits/app --release --shot /tmp/daily-limits.png
# probes: add --target lib/main_probe.dart (or main_probe_shutdown.dart)
```

Release signing reads `android/key.properties` (gitignored, a copy of
`~/.android/release/key.properties`); without it the build falls back to the
debug key. **A debug build cannot use Google sign-in** (unregistered SHA-1).
Never uninstall to switch keys: it wipes the session and unpins the widget.

## Driving it over adb

- `phone_deploy.sh` may leave the app on a virtual display. First `adb shell
  am start --display 0 -n com.kuhy.daily_limits/.MainActivity`;
  `adb shell input` needs `-d 0`.
- Do **not** force-stop to test background: it cancels the WorkManager job and
  the alarms until the next launch. Background the app, then `am kill`.
- WorkManager will not run the periodic job early: `cmd jobscheduler run -f -n
  androidx.work.systemjobscheduler com.kuhy.daily_limits <id>` leaves it
  ENQUEUED. Wait for the natural ~15-min run.

## Sign-in

Google only: the sync account is Google-only (email + password fails with
`INVALID_LOGIN_CREDENTIALS`). It needs the Android OAuth client `daily-limits`
in `kuhy-syncs` (`com.kuhy.daily_limits` + the release SHA-1); without it
sign-in fails as "canceled: account reauth failed". Google has no create API,
so `../scripts/register_oauth_client.sh` derives the SHA-1 from the keystore,
feeds the console form via the clipboard and verifies on the phone (`--sha1`,
`--verify-only`).

## Icon and focus mode

Shared family hourglass (`python_pkg/app_icons` in testsAndMisc, key
`daily_limits`). Regenerate (the system dart fails `dart run`):

```console
PATH=~/sdk/fvm/versions/3.47.7/bin:$PATH PYTHONPATH=~/src/testsAndMisc \
  python3 -m python_pkg.app_icons generate --app daily_limits --android
```

`com.kuhy.daily_limits` is whitelisted in `~/src/phone-focus-mode/config_whitelist.sh`.

## Testing

`flutter test --coverage` from `app/`. 100 % line coverage, enforced in CI
(`.github/workflows/app.yml`); entry points carry `// coverage:ignore-file`.
No mocking library: plugins are faked at their method channels
(`test/support/fakes.dart`), so the real plugin Dart code runs.

## Known limitations

- `LocalCache.save()` merges `requests` with the on-disk copy by id (answered
  beats timed out beats pending). That narrows the cross-isolate lost-write race to the gap
  between its re-read and its rename; it does not close it (no cross-isolate
  lock).
- The shutdown icon is 🔌, not the PC's ⏻: Android has no glyph for ⏻.
- The rest-day notification body still starts with "refused:" (the card strips
  it).
