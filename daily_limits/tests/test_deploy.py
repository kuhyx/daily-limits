# Copyright (c) 2026 Krzysztof Rudnicki
"""``scripts/deploy.sh`` against stub ``git``, ``systemctl`` and ``adb``.

The live checkout, ``install.sh``, ``phone_deploy.sh`` and ``capped.sh`` live
under a temp ``HOME``; every stub logs its argv to one file, so a test can
assert what ran, in which order, and what never ran (uninstall, pm clear).
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "deploy.sh"
PKG = "com.kuhy.daily_limits"

GIT_STUB = r"""#!/bin/bash
echo "git $*" >> "$STUB_LOG"
case "$*" in
  *"status --porcelain"*) [[ -n ${STUB_DIRTY:-} ]] && echo " M x.py"; exit 0 ;;
  *"rev-parse --abbrev-ref HEAD"*) echo "${STUB_BRANCH:-main}" ;;
  *"pull --ff-only"*) [[ -n ${STUB_DIVERGED:-} ]] && exit 128; exit 0 ;;
  *"rev-parse --short HEAD"*) echo "${STUB_HEAD:-abc1234}" ;;
  *) exit 0 ;;
esac
"""

SYSTEMCTL_STUB = r"""#!/bin/bash
echo "systemctl $*" >> "$STUB_LOG"
case "$*" in
  *"is-active"*) [[ -n ${STUB_INACTIVE:-} ]] && { echo inactive; exit 3; }; echo active ;;
  *"start daily-limits.service"*)
    [[ -n ${STUB_SERVICE_FAIL:-} ]] && exit 1
    echo '{"ok": true}' > "$XDG_RUNTIME_DIR/daily-limits.json" ;;
esac
exit 0
"""

ADB_STUB = r"""#!/bin/bash
echo "adb $*" >> "$STUB_LOG"
case "$*" in
  *get-state*) [[ -n ${STUB_NO_PHONE:-} ]] && exit 1; echo device ;;
  *"dumpsys package"*) echo "    versionCode=$(cat "$STUB_VC") minSdk=24 targetSdk=36" ;;
  *pidof*) [[ -z ${STUB_NOT_RUNNING:-} ]] && echo 4242 ;;
  *"shell date"*) echo 1700000000 ;;
  *logcat*) [[ -n ${STUB_CRASH:-} ]] && echo "FATAL EXCEPTION: main" && echo "Process: com.kuhy.daily_limits, PID: 1" ;;
esac
exit 0
"""

PHONE_DEPLOY_STUB = r"""#!/bin/bash
echo "phone_deploy $*" >> "$STUB_LOG"
[[ "$*" == *"--stage install"* ]] && echo $(( $(cat "$STUB_VC") + 1 )) > "$STUB_VC"
exit 0
"""

CAPPED_STUB = r"""#!/bin/bash
echo "capped CAP_MEM=${CAP_MEM:-} $1" >> "$STUB_LOG"
exec "$@"
"""

INSTALL_STUB = r"""#!/bin/bash
echo "install.sh $*" >> "$STUB_LOG"
[[ -n ${STUB_INSTALL_FAIL:-} ]] && exit 1
exit 0
"""


@dataclass
class Rig:
    """The temp HOME, the env the script runs with and the stub log."""

    home: Path
    env: dict[str, str]
    log: Path
    stamp: Path

    def run(self, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        """Run deploy.sh with the rig's env plus ``extra`` stub switches."""
        return subprocess.run(
            ["/bin/bash", str(SCRIPT), *args],
            env={**self.env, **extra},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def calls(self) -> list[str]:
        """Every stub call so far, in order."""
        return self.log.read_text().splitlines() if self.log.exists() else []


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)


@pytest.fixture
def rig(tmp_path: Path) -> Rig:
    """A temp HOME with every external command stubbed."""
    home = tmp_path / "deploy_home"
    bin_dir = tmp_path / "deploy_bin"
    runtime = tmp_path / "deploy_run"
    runtime.mkdir()
    _exe(bin_dir / "git", GIT_STUB)
    _exe(bin_dir / "systemctl", SYSTEMCTL_STUB)
    _exe(bin_dir / "adb", ADB_STUB)
    _exe(home / ".claude" / "scripts" / "phone_deploy.sh", PHONE_DEPLOY_STUB)
    _exe(home / ".claude" / "scripts" / "capped.sh", CAPPED_STUB)
    _exe(home / "src" / "daily-limits" / "install.sh", INSTALL_STUB)
    (home / "src" / "daily-limits" / "app").mkdir()
    vc = tmp_path / "vc"
    vc.write_text("7\n")
    log = tmp_path / "calls.log"
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(home),
        "XDG_RUNTIME_DIR": str(runtime),
        "STUB_LOG": str(log),
        "STUB_VC": str(vc),
        "DEPLOY_SETTLE_SECS": "0",
    }
    return Rig(home, env, log, home / ".cache" / "daily-limits-deploy" / "phone.stamp")


def _built(calls: list[str]) -> bool:
    return any(c.startswith("phone_deploy") for c in calls)


def test_full_deploy_builds_installs_and_stamps(rig: Rig) -> None:
    done = rig.run()
    assert done.returncode == 0, done.stderr
    calls = rig.calls()
    stages = [
        c.split("--stage ")[1].split()[0] for c in calls if c.startswith("phone_deploy")
    ]
    assert stages == ["prep", "dart", "kotlin", "assemble", "install"]
    assert "capped CAP_MEM=4G" in "\n".join(calls)
    # Desktop first: install, restart, one service run, then the phone.
    first_adb = next(i for i, c in enumerate(calls) if c.startswith("adb"))
    service = calls.index("systemctl --user start daily-limits.service")
    assert calls.index("install.sh ") < service < first_adb
    assert rig.stamp.read_text().split()[:2] == ["abc1234", "8"]


def test_second_run_skips_the_build_but_checks_health(rig: Rig) -> None:
    assert rig.run().returncode == 0
    rig.log.unlink()
    done = rig.run()
    assert done.returncode == 0, done.stderr
    calls = rig.calls()
    assert not _built(calls)
    assert any("dumpsys package" in c for c in calls)
    assert any("logcat" in c for c in calls)


def test_new_head_rebuilds(rig: Rig) -> None:
    assert rig.run().returncode == 0
    rig.log.unlink()
    assert rig.run(STUB_HEAD="def5678").returncode == 0
    assert _built(rig.calls())


def test_failing_desktop_health_check_exits_nonzero_before_phone(rig: Rig) -> None:
    for switch in ("STUB_INACTIVE", "STUB_SERVICE_FAIL", "STUB_INSTALL_FAIL"):
        rig.log.unlink(missing_ok=True)
        done = rig.run(**{switch: "1"})
        assert done.returncode != 0, switch
        assert not any(c.startswith("adb") for c in rig.calls()), switch


def test_stale_cache_fails_the_desktop_check(rig: Rig, tmp_path: Path) -> None:
    # The service "runs" but never rewrites the cache: an old file must not pass.
    systemctl = tmp_path / "deploy_bin" / "systemctl"
    systemctl.write_text(
        SYSTEMCTL_STUB.replace("echo '{\"ok\": true}' >", ": >/dev/null #")
    )
    cache = Path(rig.env["XDG_RUNTIME_DIR"]) / "daily-limits.json"
    cache.write_text("{}")
    os.utime(cache, (1_000_000_000, 1_000_000_000))
    assert rig.run().returncode != 0


def test_missing_phone_fails_after_desktop_passed(rig: Rig) -> None:
    done = rig.run(STUB_NO_PHONE="1")
    assert done.returncode != 0
    assert "systemctl --user start daily-limits.service" in rig.calls()
    assert "phone" in done.stderr.lower()
    assert not _built(rig.calls())


def test_phone_health_failures_exit_nonzero_and_leave_no_stamp(rig: Rig) -> None:
    for switch in ("STUB_NOT_RUNNING", "STUB_CRASH"):
        done = rig.run(**{switch: "1"})
        assert done.returncode != 0, switch
        assert not rig.stamp.exists(), switch


@pytest.mark.parametrize("switch", ["STUB_DIRTY", "STUB_DIVERGED", "STUB_BRANCH"])
def test_unclean_checkout_stops_before_any_change(rig: Rig, switch: str) -> None:
    done = rig.run(**{switch: "feature" if switch == "STUB_BRANCH" else "1"})
    assert done.returncode != 0
    calls = rig.calls()
    assert not any(
        c.startswith(("systemctl", "adb", "install.sh", "phone_deploy")) for c in calls
    )


def test_targets_run_one_half(rig: Rig) -> None:
    assert rig.run("desktop").returncode == 0
    assert not any(c.startswith("adb") for c in rig.calls())
    rig.log.unlink()
    assert rig.run("phone").returncode == 0
    assert not any(c.startswith(("systemctl", "install.sh")) for c in rig.calls())


def test_never_uninstalls_or_clears(rig: Rig) -> None:
    rig.run()
    rig.run(STUB_HEAD="def5678")
    adb = [c for c in rig.calls() if c.startswith("adb")]
    assert adb
    for text in [*adb, SCRIPT.read_text()]:
        assert " uninstall" not in text
        assert "pm clear" not in text
