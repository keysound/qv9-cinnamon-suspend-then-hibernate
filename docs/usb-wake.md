# USB wake hook / USB 喚醒設定

The tested QV9 had an independent `/usr/lib/systemd/system-sleep/qv9-usb-wake`
hook that temporarily disabled xHCI wake while the lid was closed and restored
its prior value after sleep. This was useful with USB accessories attached.

Logs verified two distinct phases of `SuspendThenHibernate`:
- 23:13:52: close-lid s2idle; xHCI wake disabled
- 23:43:53: resume to switch sleep states; wake restored, then disabled again
- 00:04:52: post-hibernate resume; wake restored

**The precise live hook was not available in the source snapshot used to
prepare this repository.** It is intentionally *not* replaced by a guessed
implementation. Follow-up contribution should import the exact audited source,
review path assumptions, and document power/wakeup permission behavior.

Device node `0000:00:14.0` is QV9-specific. Find your own device and
test separately before disabling wake sources. Some systems require USB input
to recover from suspend, and changing this setting can strand a device.

此目錄暫時只有說明，不提供推測的 hook 原始碼。公開時不能把尚未
核對的程式標成「實機驗收版」。
