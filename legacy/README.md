# Historical recovery and login scripts

This directory preserves three scripts/configuration fragments from an earlier QV9 power-management design.

**These files are not prerequisites for Cinnamon's built-in SuspendThenHibernate.** They are retained so the original setup can be studied and backed up, not as a recommended installation set.

| File | Historical purpose |
| --- | --- |
| `qv9-cinnamon-lid-defaults` | At graphical login, set both Cinnamon lid-close actions to `suspend`. |
| `restore-cinnamon-lid.sh` | Restore the same actions when the custom Handler service stops. |
| `10-fallback.conf` | Example systemd user-service drop-in invoking the restoration script from `ExecStopPost`. |

Both shell scripts contain a `qv9-lid-owner.lock` / `flock` mechanism originally used to coordinate an ownership takeover design. **The released v0.8.4-e1 Handler does not take over the lid-switch inhibitor**, so that lock is legacy coordination rather than part of the native S4 pathway.

## Why not install these by default?

- Both scripts **write** the user's Cinnamon lid-close policy. That can override a different, intentional desktop configuration.
- The service drop-in runs a restoration command whenever the service stops, which is not appropriate for every user's session lifecycle.
- These scripts do not enable `suspend-then-hibernate=true`, configure `HibernateDelaySec`, or make swap-based hibernation work.
- Their behavior was retained on the tested QV9 as a conservative compatibility choice; that is not evidence they are required elsewhere.

For a new system, first configure and test the **native** Cinnamon/systemd pathway described in the [README](../README.md). If you choose to adapt these historical scripts, inspect their effects and arrange your own backups and rollback.

The optional observer implementation lives in [`handler/lid-handler.py`](../handler/lid-handler.py); the overall architecture is documented in [Architecture](../docs/architecture.md).
