# Safety and recovery

- Always back up your original settings and files before experimentation.
- Test manual hibernate and resume before enabling automatic S4.
- Keep AC power attached during initial tests; save documents and be present.
- Start with a brief Suspend/Resume while the lid is **open**, then test
  a short lid cycle, and only then a full timed cycle.
- Keep the original Cinnamon lid actions available as a conservative fallback.
- Capture `journalctl -b -u systemd-suspend-then-hibernate.service`,
  `journalctl -b -k` and your handler service logs for diagnosis.
- If Cinnamon's native S4 policy is causing trouble, the simple feature
  toggle is `gsettings set org.cinnamon.SessionManager suspend-then-hibernate false`.
  This does **not** repair a broken hibernate image or swap configuration.
- Never use this example as proof of lid wake behavior for another device.
- The included legacy fallback and login defaults were part of the tested
  machine and retain old ownership-flock logic. Preserve as reference,
  not a fresh recommendation.
