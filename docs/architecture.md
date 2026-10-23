# Architecture / 架構

```text
Lid closes
   |
   +-- Cinnamon power manager --(Lock/Suspend)--> logind.SuspendThenHibernate
   |                                                |
   |                                           systemd-sleep
   |                                             s2idle (30 min)
   |                                                |
   |                                           Hibernate (S4)
   |
   +-- Optional observer-only Python handler
         logind LidClosed / PrepareForSleep
         Cinnamon ScreenSaver Lock + ActiveChanged
         (no suspend/hibernate request, no lid inhibitor)
```

- `HandleLidSwitch=suspend` is an intentionally conservative logind safety
  override in this tested case. Under ordinary Cinnamon use,
  `csd-power` holds `handle-lid-switch` block inhibitor.
- `inhibit-lid-switch=false` is NOT a reliable immediate handover: on tested
  Cinnamon 6.6.4 it did not release the existing inhibitor FD.
- Screensaver reports active before entering sleep; visual lock behavior
  was also checked on resume in the QV9 test.
- The originally deployed USB wake hook (not included) handled both
  pre/post suspend and pre/post hibernate calls.

The original experiment spent time exploring flock-based ownership of the
lid-switch inhibitor. The final working architecture did **not** use that
ownership protocol. The Python script is intentionally observer-only.
