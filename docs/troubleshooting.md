# Troubleshooting SuspendThenHibernate

This guide starts with **observable symptoms**, not with assumptions about which component is broken. Save work and do not repeat a long-duration sleep test until the smaller checks pass.

## Quick snapshot

Run these from the affected machine's Cinnamon desktop session:

```bash
printf '\n== Cinnamon ==\n'
gsettings get org.cinnamon.SessionManager suspend-then-hibernate
gsettings get org.cinnamon.SessionManager prefer-hybrid-sleep
gsettings get org.cinnamon.settings-daemon.plugins.power lid-close-ac-action
gsettings get org.cinnamon.settings-daemon.plugins.power lid-close-battery-action

printf '\n== Systemd ==\n'
systemd-analyze cat-config systemd/sleep.conf
systemd-analyze cat-config systemd/logind.conf

printf '\n== Lid ownership ==\n'
systemd-inhibit --list --no-pager

printf '\n== Sleep service ==\n'
journalctl -b -u systemd-suspend-then-hibernate.service --no-pager
```

### Symptom: Suspend works, but never transitions to S4

Check whether the action reached `systemd-suspend-then-hibernate.service`, not just `systemd-suspend.service`.

Check the effective `HibernateDelaySec`, Cinnamon's `suspend-then-hibernate` switch, `prefer-hybrid-sleep`, and real hibernation support:

```bash
busctl --system call org.freedesktop.login1 /org/freedesktop/login1 \
  org.freedesktop.login1.Manager CanSuspendThenHibernate
journalctl -b -k --no-pager | grep -Ei 'PM: suspend|PM: hibernat|swsusp|resume'
```

A `CanSuspendThenHibernate=yes` response and a started service are **not** proof of hibernation. If the kernel never logs hibernation entry, diagnose the effective systemd policy and the platform's timed-wake behavior before adjusting unrelated scripts.

### Symptom: The machine attempts S4 but cannot resume

Treat this as a **manual hibernate/resume** issue first. Verify your own swap capacity, resume device mapping, kernel boot parameters, firmware, and image restoration. This repository does not contain a portable recipe for those settings.

Inspect the correct boot's kernel messages (`journalctl --list-boots`, then `-b` or `-b -1`). Avoid copying the tested QV9's `resume=UUID` or `resume_offset`.

Disable Cinnamon's automatic SuspendThenHibernate while investigating:

```bash
gsettings set org.cinnamon.SessionManager suspend-then-hibernate false
```

### Symptom: Closing the lid causes immediate wake or a second suspend

Check for competing lid owners and repeated lid events:

```bash
systemd-inhibit --list --no-pager
journalctl -b -u systemd-suspend-then-hibernate.service --no-pager
journalctl -b -k --no-pager | grep -Ei 'PM: suspend|wakeup|resume'
```

The tested QV9 relied on Cinnamon's `csd-power` owning `handle-lid-switch`. A separate logind lid policy, another power manager, or a USB wake source can change behavior. **Do not blindly disable USB wake sources**; first identify the responsible device. See [USB wake behavior](usb-wake.md).

### Symptom: The desktop appears before the lock screen

Check Cinnamon's native lock policy and the observed ScreenSaver state. The tested QV9 used:

```bash
gsettings get org.cinnamon.settings-daemon.plugins.power lock-on-suspend
gsettings get org.cinnamon.desktop.screensaver lock-enabled
gsettings get org.cinnamon.desktop.screensaver lock-delay
```

The optional monitor can request `org.cinnamon.ScreenSaver.Lock`, but its `LOCK ready` log only records D-Bus acknowledgement and ScreenSaver-reported state. It is not a guarantee of a rendered frame before suspension. Verify the actual wake experience before treating the lock behavior as secure. Password/PIN policy is configured separately.

### Symptom: The optional Python Handler does not start

```bash
systemctl --user status qv9-lid-handler.service
journalctl --user -b -u qv9-lid-handler.service --no-pager
python3 handler/test-stage-e1.py
```

Confirm the installed script path matches `systemd/qv9-lid-handler.service`, `python3-gi` is installed, and the user service runs within the intended Cinnamon session. The 11 isolated tests do **not** establish a working session D-Bus connection or live lid notifications.

**Do not introduce another sleep request into the Handler** to compensate for a Cinnamon/systemd problem. It is intentionally observer-only.

## After reboot or hibernate resume

If the current boot contains no relevant events:

```bash
journalctl --list-boots
journalctl -b -1 -u systemd-suspend-then-hibernate.service --no-pager
journalctl -b -1 -k --no-pager | grep -Ei 'PM: suspend|PM: hibernat|resume'
```

These commands require that the previous boot's journal is available.

## Reporting a reproducible problem

Useful reports include the laptop model, OS/Cinnamon/systemd/kernel versions, which user action triggered sleep, expected versus actual behavior, effective policy values, `systemd-inhibit` output, and a small window of relevant logs.

**Remove identifying or sensitive data before posting logs.** For safe testing and rollback, see [Safety and recovery](security-and-recovery.md).
