# Development notes: how this design was selected

This page records the engineering decisions behind the tested QV9 configuration. It is **background reading**, not a setup procedure. For instructions, start with the [README](../README.md).

## Problem statement

The desired user experience was:

- Closing the lid locks the session and enters suspend.
- After 30 minutes, the computer enters hibernation (S4).
- Opening the lid resumes to the lock screen, with the previous desktop intact.
- USB peripherals do not unexpectedly wake the laptop while its lid is closed.
- Reboot or service restart does not introduce a second suspend or a new lid-policy owner.

The difficult part was coordinating Cinnamon, logind, systemd, screen locking, and hardware wake behavior, not writing a hibernation image directly.

## Approaches evaluated

### Separate lid ownership in a custom Handler

An early design explored a Python controller owning the logind `handle-lid-switch` inhibitor, coordinating state transitions such as SAFE/ARMING/OWNED and serializing fallback behavior with `flock`.

This creates additional responsibilities: takeover order, inhibitor lifetime, crashes, stale state, and interaction with the Cinnamon power daemon. The old model was **not enabled as an actual S4 issuer** on the final tested system.

### Delegating everything to logind

The team also tested whether changing Cinnamon's `inhibit-lid-switch` setting would immediately surrender its existing lid inhibitor. On Cinnamon 6.6.4, changing the GSettings value alone did not remove the current `csd-power` inhibitor. Cinnamon also retained its own configured lid action. The resulting ownership handoff was not adopted.

### Native Cinnamon SuspendThenHibernate (chosen)

Source inspection and actual QV9 tests established that Cinnamon's power path can use `org.cinnamon.SessionManager suspend-then-hibernate=true` and request logind's `SuspendThenHibernate`.

This removed the need to make the Python Handler a second power manager:

- Cinnamon remains the lid-policy owner.
- systemd handles the timed suspend-to-hibernate transition.
- The optional Handler requests screen locking and observes transitions.
- The device-specific USB hook handles peripheral wake behavior separately.

The retained logind `HandleLidSwitch=suspend` override serves as a conservative fallback for the tested configuration, **not** as the source of automatic S4.

## Versions and verification

| Revision / phase | Role | Evidence |
| --- | --- | --- |
| v0.8.2 | Ownership research and dry-run prototype, `ENABLE_S4=False`. | No deployed owned-lid S4 path. |
| v0.8.3-b1 | Observer-only Handler; Cinnamon owns lid and sleep. | 11 isolated regression tests; short cycles; complete 30-minute S4/resume test on Oct 23–24, 2026. |
| v0.8.4-e1 | Log message and naming cleanup without an intended sleep-path change. | 11 isolated tests, deployed service startup, and configuration persistence after reboot. |

In the complete timed test:

- 23:13:52: lid close → s2idle
- 23:43:53: timed transition → hibernation
- 00:04:52: lid-open resume → PIN lock screen and preserved desktop

The complete 30-minute cycle was **not rerun** specifically for v0.8.4-e1. The PIN/PAM customization and the exact tested USB hook are not distributed here.

## Lessons for similar investigations

1. Identify which component actually owns the lid before adding a second power manager.
2. Inspect the desktop environment's existing suspend behavior before implementing a competing state machine.
3. Distinguish D-Bus acceptance, ScreenSaver state, systemd service activity, and actual kernel S4 entry. Each proves something different.
4. Test short transitions before a timed S4 cycle, then test settings persistence after reboot.
5. Keep historical scripts isolated from the recommended path so that backup/reference code is not mistaken for a necessary installation step.

For the current architecture, see [Architecture](architecture.md). For old compatibility scripts, see [Legacy scripts](../legacy/README.md).
