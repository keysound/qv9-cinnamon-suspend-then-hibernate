# Power-management architecture

This page describes the responsibilities of Cinnamon, logind, systemd, the optional Python monitor, and the lock screen in the **tested QV9 configuration**.

## Sleep and screen locking are separate paths

```text
Laptop lid closes
       |
       +--> Cinnamon power manager (csd-power)
       |       |
       |       +--> Cinnamon ScreenSaver lock request
       |       |
       |       +--> logind: SuspendThenHibernate()
       |                    |
       |                    v
       |             systemd-sleep
       |                    |
       |             s2idle / suspend
       |                    |
       |           HibernateDelaySec=30min
       |                    |
       |             hibernate (S4)
       |
       +--> optional lid-handler.py
               |
               +--> observe logind LidClosed property changes
               +--> request Cinnamon ScreenSaver Lock if needed
               +--> observe PrepareForSleep and ScreenSaver state
               +--> log state transitions
               (no sleep request; no lid-switch inhibitor)
```

The branches are conceptually parallel. Do **not** read the diagram as a guaranteed ordering barrier between ScreenSaver rendering and entry into sleep.

## Component responsibilities

| Component | Role |
| --- | --- |
| `csd-power` | Handles the lid-close `suspend` action and its own screen-lock policy. |
| `org.cinnamon.SessionManager` GSettings | Selects `suspend-then-hibernate=true` and `prefer-hybrid-sleep=false` for Cinnamon-initiated Suspend. |
| `systemd-logind` | Exposes the `SuspendThenHibernate` D-Bus operation, handles inhibitors, and coordinates sleep. |
| `systemd-sleep` | Executes the initial suspend and later hibernate, subject to effective sleep configuration and machine capabilities. |
| Linux kernel and firmware | Perform s2idle, hibernation image save/restore, and platform-specific wake/resume. |
| Cinnamon ScreenSaver / PAM | Present the lock screen and authenticate the returning user. PIN authentication was configured separately on the QV9; it is not part of this repository. |
| Optional `lid-handler.py` | Monitors events and requests lock; it never issues Suspend/Hibernate or acquires the lid-switch inhibitor. |

## Why logind does not also handle the lid

On the tested QV9, Cinnamon was configured with:

```text
org.cinnamon.settings-daemon.plugins.power inhibit-lid-switch = true
lid-close-ac-action = 'suspend'
lid-close-battery-action = 'suspend'
```

At boot, `systemd-inhibit --list` showed `csd-power` holding `handle-lid-switch` as a **block** inhibitor, while no inhibitor belonged to the Python Handler. This is the key distinction: Cinnamon handles the lid action, and logind performs the requested sleep operation.

The system also retained the conservative logind fallback `HandleLidSwitch=suspend`. That fallback does **not** enable SuspendThenHibernate by itself. If Cinnamon does not own the lid, behavior can change.

Do not assume that editing `inhibit-lid-switch` releases a previously opened inhibitor FD immediately. In Cinnamon 6.6.4 on this machine, changing the setting did not release the existing inhibitor without restarting the relevant process.

Useful read-only checks:

```bash
systemd-inhibit --list --no-pager
systemd-analyze cat-config systemd/logind.conf
systemd-analyze cat-config systemd/sleep.conf
gsettings get org.cinnamon.SessionManager suspend-then-hibernate
gsettings get org.cinnamon.SessionManager prefer-hybrid-sleep
```

## What the optional Handler actually observes

The Handler uses:

- logind's `org.freedesktop.DBus.Properties.PropertiesChanged` signal for the `LidClosed` **property**;
- logind Manager's `PrepareForSleep` signal;
- Cinnamon ScreenSaver's `ActiveChanged` signal and `GetActive` / `Lock` methods.

The Handler's `LOCK ready` message means its internal conditions were met, including a successful Lock request and ScreenSaver-reported active state. It is **not** independent proof that the final lock frame was already rendered to the display.

## Evidence and limits

The QV9 logs showed:

- 2026-10-23 23:13:52: systemd began `suspend-then-hibernate`; kernel entered `s2idle`.
- 2026-10-23 23:43:53: kernel left suspend and entered hibernation.
- 2026-10-24 00:04:52: kernel returned from hibernation; user observed the PIN lock screen, preserved session, and no second suspend.

The complete timed cycle was run with Handler **v0.8.3-b1**. The deployed **v0.8.4-e1** retained the same sleep-control architecture and passed offline/startup/reboot tests; a second complete 30-minute cycle with that exact revision was not recorded.

For why the earlier ownership-based approach was abandoned, see [Development notes](development-notes.md). For operational symptoms, see [Troubleshooting](troubleshooting.md).
