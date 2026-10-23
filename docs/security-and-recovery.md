# Safety, rollback, and data protection

Power-management changes can interrupt work or prevent a laptop from resuming. Treat the configuration in this repository as a reference for the **tested QV9**, not a safe default for other computers.

## Before changing the system

1. Back up files you intend to modify and record existing GSettings values.
2. Establish **working manual hibernate and resume** first. This repository does not configure swap, kernel `resume=`, or `resume_offset`.
3. Test while present at the laptop, with AC power connected and documents saved.
4. Avoid simultaneous changes to Cinnamon lid policy, logind inhibitor ownership, USB wake sources, and sleep configuration. Change one layer at a time.
5. Keep a recovery method that does not depend on the lid behaving as expected.

Recommended test order: open-lid short Suspend/Resume → short lid-close/reopen → full timed SuspendThenHibernate/Resume.

## Disable Cinnamon's automatic S4 policy

From a working Cinnamon desktop session:

```bash
gsettings set org.cinnamon.SessionManager suspend-then-hibernate false
gsettings get org.cinnamon.SessionManager suspend-then-hibernate
```

This disables the **Cinnamon policy choice**; it does not disable every possible system hibernation command or fix underlying swap/resume failures.

If you previously changed `prefer-hybrid-sleep` or either lid-close action, restore **your recorded original values** rather than assuming the QV9's values fit your machine.

## Collect logs before making further changes

```bash
journalctl --list-boots
journalctl -b -u systemd-suspend-then-hibernate.service --no-pager
journalctl -b -k --no-pager | grep -Ei 'PM: suspend|PM: hibernat|swsusp|resume'
systemd-inhibit --list --no-pager
systemd-analyze cat-config systemd/logind.conf
systemd-analyze cat-config systemd/sleep.conf
```

After a real reboot, the relevant failed cycle may be in `journalctl -b -1`, not the current boot.

If you use the optional Handler:

```bash
systemctl --user status qv9-lid-handler.service
journalctl --user -b -u qv9-lid-handler.service --no-pager
```

`LOCK ready` is a Handler state message, **not** proof of a successful suspend, hibernate, or final on-screen lock rendering.

## Source code versus system backup

GitHub preserves these **public source and example files**. It does not preserve your live swapfile, kernel boot parameters, private PAM configuration, installed services, system secrets, or all systemd overrides.

Back up and test recovery of actual machine configuration separately. Before posting diagnostic logs publicly, remove hostnames, usernames, home paths, UUIDs, serial numbers, and any tokens or other private details.

## Scope

The complete 30-minute test used the earlier v0.8.3-b1 Handler; the published v0.8.4-e1 received offline, deployment, and reboot-persistence checks. Long-term repeats, battery-only endurance, external displays/docks, and session-failure recovery have not been established.

See [Troubleshooting](troubleshooting.md) for symptom-specific checks.
