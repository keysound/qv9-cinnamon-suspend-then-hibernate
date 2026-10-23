# QV9 Cinnamon Suspend → Hibernate

[繁體中文說明](README.zh-TW.md)

A **tested case study and reference implementation**, not a universal one-click
hibernate installer, for Linux Mint 22.3 Cinnamon on a Panasonic Let's note QV9.

## What actually makes S4 work?

**Cinnamon and systemd do the sleeping.** The optional Python lid handler only
requests the Cinnamon screen lock and records lifecycle events. It **never**
calls `Suspend`, `Hibernate`, `SuspendThenHibernate`, or obtains a logind
`handle-lid-switch` inhibitor.

The primary switch is Cinnamon's built-in:

```bash
gsettings set org.cinnamon.SessionManager suspend-then-hibernate true
```

When Cinnamon handles a `suspend` action with this switch enabled, its power
helper can call logind's `SuspendThenHibernate`. systemd manages the timer and
the transition from suspend to hibernation. This setting affects Cinnamon's
suspend policy generally, **not just lid-close**.

### Verified hardware and software

- Panasonic Let's note QV9
- Linux Mint 22.3, Cinnamon 6.6.9, cinnamon-settings-daemon 6.6.4,
  cinnamon-session 6.6.3, systemd 255
- Kernel 7.0.0-38-generic with a previously working local swapfile S4/resume setup
- `HibernateDelaySec=30min`
- Optional Python handler v0.8.4-e1 (`handler/lid-handler.py`)

Observed on 2026-10-23/24:
1. Lid closure invoked `systemd-suspend-then-hibernate.service` and entered s2idle.
2. Approximately 30 minutes later the kernel entered hibernation.
3. Opening the lid resumed the prior desktop and displayed the PIN lock screen.
4. No second suspend was observed.
5. After reboot, the configuration and observer-only handler started as expected.

**Evidence scope:** One complete long-duration S4 cycle plus shorter suspend
tests and a reboot persistence test. This does not prove reliability for other
laptops, batteries, docks, distributions, or a broken hibernate configuration.

## Before trying anything

**Never copy someone else's `resume=UUID`, `resume_offset` or swap configuration.**
First make **manual hibernate and resume** work on your own device. Back up
your work, keep AC connected for testing, and learn your recovery path.

Useful read-only checks:

```bash
busctl --system call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager CanSuspend
busctl --system call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager CanHibernate
busctl --system call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager CanSuspendThenHibernate
systemd-analyze cat-config systemd/sleep.conf
systemd-analyze cat-config systemd/logind.conf
systemd-inhibit --list
```

Expected capability responses were `s "yes"` on the tested QV9. Even that is
**not proof** that firmware, RTC wake, storage, and resume will work.

## Example Cinnamon policy

Only after manual S4/resume is proven, inspect the current values:

```bash
gsettings get org.cinnamon.SessionManager suspend-then-hibernate
gsettings get org.cinnamon.SessionManager prefer-hybrid-sleep
gsettings get org.cinnamon.settings-daemon.plugins.power inhibit-lid-switch
gsettings get org.cinnamon.settings-daemon.plugins.power lid-close-ac-action
gsettings get org.cinnamon.settings-daemon.plugins.power lid-close-battery-action
```

The tested QV9 used `true`, `false`, `true`, `'suspend'`, `'suspend'`.
The first setting can be **reverted** with:

```bash
gsettings set org.cinnamon.SessionManager suspend-then-hibernate false
```

The examples under `examples/` record our systemd configuration. They are
**reference snippets, not automated installers**. They may be inappropriate
for different systemd versions or hardware.

## Optional observer / lock helper

`handler/lid-handler.py` is the precise v0.8.4-e1 reviewed candidate deployed
and startup-tested on QV9. It subscribes to logind `LidClosed` /
`PrepareForSleep` signals and the Cinnamon ScreenSaver. It requests a lock on
lid close and tracks a small state machine. It **does not own sleep policy**.

Dependencies on a compatible Cinnamon/X11 session include Python 3 and
PyGObject (`python3-gi`). A reference user service is in `systemd/`.
It intentionally is not installed by a one-click script. Review the paths
and dependencies before any deployment.

Offline regression tests (no sleep is triggered):

```bash
python3 handler/test-stage-e1.py
```

The original project also used a separate USB xHCI wake hook on PCI address
`0000:00:14.0` to avoid peripheral wakeups with the lid closed. **Its exact
deployed source has not yet been supplied to this public package.** Do not
infer that it is installed by this repository or copy that PCI address
without checking your machine. See [USB wake notes](docs/usb-wake.md).

## Legacy recovery scripts

`legacy/` contains historical QV9 fallback/login scripts. They preserve
Cinnamon `lid-close-*-action='suspend'` and use an older ownership flock.
They are retained for provenance and backup; **do not install or enable them
blindly**. They are not required by Cinnamon's native S4 feature.

## Known boundaries

- Device-specific suspend and hibernate configuration; no general installer.
- The lock handler is best-effort; do not treat a screensaver `active` signal
  as proof of complete on-screen rendering.
- No guarantee for multi-monitor/docked, other desktop environments, battery
  duration, repeated cycles, session crashes, or secure lid wake behavior.
- GitHub is source/version history backup, **not a replacement for an offline
  system-state backup** or verification of your swap/bootloader configuration.

See [architecture](docs/architecture.md).

## License

MIT. Hardware-specific configuration examples come with **no guarantee**.
