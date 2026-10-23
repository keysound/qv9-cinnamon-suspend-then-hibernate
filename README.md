# Suspend then Hibernate on Linux Mint Cinnamon (Panasonic QV9)

[繁體中文](README.zh-TW.md) | [Architecture](docs/architecture.md) | [Troubleshooting](docs/troubleshooting.md)

This repository documents a working **suspend → timed hibernate (S4) → resume** configuration on a Panasonic Let's note QV9 running Linux Mint 22.3 Cinnamon. It contains an optional lid-lock event monitor, sample systemd settings, and tests.

**The S4 transition is provided by Cinnamon and systemd, not by the Python script.** This is a hardware-specific reference, not a universal hibernation installer.

## Tested setup and result

| Component | Tested configuration |
| --- | --- |
| Hardware | Panasonic Let's note QV9 |
| Desktop | Linux Mint 22.3, Cinnamon 6.6.9 |
| Power/session daemons | cinnamon-settings-daemon 6.6.4, cinnamon-session 6.6.3 |
| Service manager / kernel | systemd 255 / 7.0.0-38-generic |
| Sleep mode | s2idle → hibernate (S4), delay: 30 minutes |
| Optional lid helper | `handler/lid-handler.py` v0.8.4-e1 |

On October 23–24, 2026, the QV9 entered s2idle after lid closure, transitioned to hibernation after ~30 minutes, and resumed to the locked session when the lid was opened. The prior desktop remained intact, with no second suspend observed. The v0.8.4-e1 handler later passed 11 offline tests, startup/deployment checks, and a reboot persistence check.

The **full 30-minute S4 cycle was tested with the preceding v0.8.3-b1 handler**. v0.8.4-e1 was a logging/naming cleanup; its full-duration cycle has not been independently repeated. This is one verified long-duration cycle, not a reliability guarantee across other hardware, batteries, docks, or desktop environments.

## How it works

1. Cinnamon handles the lid-close action configured as `suspend`.
2. With `org.cinnamon.SessionManager suspend-then-hibernate=true` and `prefer-hybrid-sleep=false`, Cinnamon can request logind's `SuspendThenHibernate` rather than ordinary Suspend.
3. systemd first suspends the machine and later transitions it to hibernation using `HibernateDelaySec=30min`.
4. Cinnamon's own screen-lock mechanism, with optional assistance from this repository's **observer-only** handler, locks the session. Authentication method (password/PIN) is a separate, local Cinnamon/PAM configuration.

This Cinnamon switch also affects other suspend actions initiated by Cinnamon. It is **not limited to lid-close**. See [Architecture](docs/architecture.md).

## Setup overview

### 1. Verify manual hibernate/resume first

Before enabling automatic S4, confirm that **manual hibernate and resume already work** on *your* machine. Hibernation requires suitable swap and boot/resume configuration, which this repository does not create.

Do **not** copy the QV9's swap UUID, `resume_offset`, kernel parameters, or PCI device IDs. Save your work and have a recovery procedure ready.

Check what logind reports:

```bash
for feature in CanSuspend CanHibernate CanSuspendThenHibernate; do
  printf '%s: ' "$feature"
  busctl --system call org.freedesktop.login1 /org/freedesktop/login1 \
    org.freedesktop.login1.Manager "$feature"
done
```

The tested system returned `s "yes"` for each capability. These responses alone do **not** prove that real suspend, RTC wake, hibernate-image writing, and resume will succeed.

### 2. Inspect Cinnamon ownership and existing policy

In your graphical Cinnamon session:

```bash
gsettings get org.cinnamon.SessionManager suspend-then-hibernate
gsettings get org.cinnamon.SessionManager prefer-hybrid-sleep
gsettings get org.cinnamon.settings-daemon.plugins.power inhibit-lid-switch
gsettings get org.cinnamon.settings-daemon.plugins.power lid-close-ac-action
gsettings get org.cinnamon.settings-daemon.plugins.power lid-close-battery-action
systemd-inhibit --list --no-pager
```

On the tested QV9, the final values were `true`, `false`, `true`, `'suspend'`, and `'suspend'`, respectively. `csd-power` held the `handle-lid-switch` block inhibitor, so **Cinnamon**, not logind's default lid handler, handled ordinary lid closures.

Do not change `inhibit-lid-switch` solely to imitate these values; on the tested Cinnamon version, changing it did not release an already-held inhibitor until the relevant daemon restarted. Check actual inhibitor ownership before changing policies.

### 3. Enable Cinnamon's native SuspendThenHibernate

**Only after manual S4/resume succeeds**, enable Cinnamon's policy:

```bash
gsettings set org.cinnamon.SessionManager prefer-hybrid-sleep false
gsettings set org.cinnamon.SessionManager suspend-then-hibernate true
```

The QV9's lid-close AC and battery actions were both `suspend`. To see or change yours, use Cinnamon Power Management or review the relevant `gsettings` keys above. Avoid creating competing lid handlers.

For the 30-minute delay, see [`examples/10-suspend-then-hibernate.conf`](examples/10-suspend-then-hibernate.conf). It corresponds to the systemd sleep drop-in used on the tested machine:

```ini
[Sleep]
HibernateDelaySec=30min
```

Review your existing drop-ins and the applicable systemd version before adopting the example. Confirm the effective value with:

```bash
systemd-analyze cat-config systemd/sleep.conf
```

[`examples/90-qv9-safe-suspend.conf`](examples/90-qv9-safe-suspend.conf) documents the QV9's conservative logind fallback (`HandleLidSwitch=suspend`). It **does not itself enable automatic S4**; Cinnamon's own power policy does that when Cinnamon owns the lid switch.

### 4. Test in stages

With work saved and AC power connected:

1. Try a short Suspend/Resume while the lid is **open**.
2. Try a short lid-close/reopen cycle and verify the lock screen.
3. Finally, leave the lid closed for longer than the configured delay; verify actual hibernation and resume.

Check both the service and kernel logs; a started `systemd-suspend-then-hibernate.service` is **not**, by itself, proof that S4 occurred:

```bash
journalctl -b -u systemd-suspend-then-hibernate.service --no-pager
journalctl -b -k --no-pager | grep -Ei 'PM: suspend|PM: hibernat|swsusp|resume'
```

If the system started a new boot, inspect `journalctl --list-boots` and the appropriate previous boot with `-b -1`. See [Troubleshooting](docs/troubleshooting.md).

## Optional Python lid-lock monitor

`handler/lid-handler.py` observes logind's `LidClosed` **property change** via D-Bus `PropertiesChanged`, logind's `PrepareForSleep` signal, and Cinnamon ScreenSaver state. On lid closure it can request ScreenSaver `Lock` and records its state transitions. It **does not** ask logind to suspend/hibernate and **does not** acquire a lid-switch inhibitor.

It is optional and requires a compatible Cinnamon session, Python 3, and PyGObject (`python3-gi`). The example `systemd/qv9-lid-handler.service` refers to a per-user installation at `~/.local/lib/qv9/lid-handler.py`. It is a **service example**, not an installer. The repository does not provide or configure the QV9's custom PIN/PAM authentication.

Run its isolated, non-sleeping regression tests:

```bash
python3 handler/test-stage-e1.py
```

## USB wake behavior and legacy files

The tested QV9 also ran a device-specific USB xHCI wake hook. Its **exact deployed source is not included**, so this repository makes no claim to reproduce that USB behavior. Read [USB wake notes](docs/usb-wake.md) before changing wake sources.

`legacy/` contains historical recovery/login scripts preserved for reference. They use ownership-flock coordination from an earlier design; they are not prerequisites for native S4 and should not be installed without independent review. See [Legacy scripts](legacy/README.md) and [Development notes](docs/development-notes.md).

## Recovery, scope, and license

To disable Cinnamon's **automatic** SuspendThenHibernate policy:

```bash
gsettings set org.cinnamon.SessionManager suspend-then-hibernate false
```

This switch does not repair an unrelated broken hibernate/resume configuration. For further recovery steps, see [Safety and recovery](docs/security-and-recovery.md).

**Not validated:** long-term repeatability, battery endurance, external monitors/docks, session-daemon failures, or other laptop models. GitHub source control is not a substitute for a separate private backup of your machine's system state.

Released under the [MIT License](LICENSE).
