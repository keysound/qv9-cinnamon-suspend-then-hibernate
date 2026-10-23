# USB wake behavior on the Panasonic QV9

## Problem

USB devices can be permitted to wake a laptop from suspend. On the tested QV9, attached peripherals could interfere with the desired lid-closed sleep behavior.

The working machine had an additional systemd sleep hook at:

```text
/usr/lib/systemd/system-sleep/qv9-usb-wake
```

When the lid was closed, that hook temporarily disabled wake capability for the machine's xHCI controller, then restored the previous setting after each sleep phase.

## Observed behavior

The sleep-hook logs for the complete timed cycle showed:

| Time (local) | Event |
| --- | --- |
| 2026-10-23 23:13:52 | Lid closed; xHCI wake disabled before s2idle. |
| 2026-10-23 23:43:53 | Wake setting restored after suspend; disabled again for the hibernate phase. |
| 2026-10-24 00:04:52 | After resuming from S4, the original xHCI wake setting was restored. |

This matters because `SuspendThenHibernate` involved **two** sleep-hook phases on the tested machine, not just the initial suspend.

## Source availability

**The exact deployed `qv9-usb-wake` script is not included in this repository.** The observations above come from the tested machine's journal, not from a replacement script distributed here. The repository can reproduce the Cinnamon/systemd configuration and optional observer code, but does **not** reproduce that additional QV9 USB wake behavior.

The hardware identifier `0000:00:14.0` refers to the xHCI controller checked on this QV9. It is not a portable USB device selection.

## Why copying wake settings is risky

Wake-source behavior depends on the laptop firmware, USB controller, input devices, and chosen sleep state. Disabling the wrong source may prevent expected keyboard, mouse, or lid-triggered recovery.

To investigate an unexpected wake, start by checking your device's own power and wake configuration and its system journal. Do not copy the QV9's PCI address into another computer.

For the core sleep sequence, see [Architecture](architecture.md). For diagnosis and recovery, see [Troubleshooting](troubleshooting.md).
