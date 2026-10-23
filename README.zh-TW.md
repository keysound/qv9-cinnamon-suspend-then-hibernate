# Linux Mint Cinnamon 自動休眠（S4）實作：Panasonic QV9

[English README](README.md) | [系統架構](docs/architecture.md) | [故障排除](docs/troubleshooting.md)

本專案記錄 Panasonic Let's note QV9 在 Linux Mint 22.3 Cinnamon 上，成功實現**關蓋暫停 → 30 分鐘後自動休眠（S4）→ 開蓋恢復原工作狀態**的設定與測試結果。

這是經過實機驗證的**參考案例**，不是適用所有 Linux 筆電的一鍵安裝器。

> **關鍵：S4 由 Cinnamon 原生電源管理與 systemd 完成。** 本專案的 Python Handler 是選用的關蓋鎖定輔助與事件監控程式，並不負責啟動休眠。

## 實測環境與成果

| 項目 | 實測配置 |
| --- | --- |
| 電腦 | Panasonic Let's note QV9 |
| 桌面 | Linux Mint 22.3 / Cinnamon 6.6.9 |
| Cinnamon 元件 | cinnamon-settings-daemon 6.6.4、cinnamon-session 6.6.3 |
| 系統 | systemd 255、Kernel 7.0.0-38-generic |
| 睡眠流程 | s2idle → 30 分鐘後 Hibernate（S4） |
| 選用 Handler | `handler/lid-handler.py` v0.8.4-e1 |

2026 年 10 月 23 日 23:13:52 關蓋進入 s2idle，23:43:53 自動進入 Hibernate。10 月 24 日 00:04:52 開蓋恢復，畫面先顯示 PIN 鎖定介面，原有視窗仍在，未出現二次睡眠。

**驗收範圍要分清楚：**完整 30 分鐘測試是在 Handler v0.8.3-b1 時完成；v0.8.4-e1 僅調整命名與日誌，之後通過 11 項離線測試、正式部署及重新開機持久性檢查，沒有另外重跑完整 30 分鐘測試。以上是單次完整長時間實測，不能推論其他機型或長期穩定性也一定相同。

## 工作原理

1. Cinnamon 收到關蓋事件，執行已設定的 `suspend` 動作。
2. 啟用 `org.cinnamon.SessionManager suspend-then-hibernate=true`，且 `prefer-hybrid-sleep=false` 時，Cinnamon 可經由 logind 呼叫 `SuspendThenHibernate`。
3. systemd 先暫停，達到 `HibernateDelaySec=30min` 後再轉入 S4。
4. Cinnamon Screensaver 負責鎖定畫面；選用的 Handler 可以協助要求鎖定並記錄事件。**PIN 或密碼的認證方式由電腦本身的 Cinnamon／PAM 設定決定，本專案不包含 PIN 認證設定。**

注意：`suspend-then-hibernate=true` 影響 Cinnamon 發出的其他 Suspend 動作，**不只關蓋時有效**。細節見[系統架構](docs/architecture.md)。

## 設定與驗證

### 1. 先確認手動 S4 能正常往返

**請先在自己的電腦上成功測試「手動 Hibernate → Resume」**，再設定自動 S4。本專案不會替你建立 swapfile，也不會設定開機時所需的 resume 參數。

不要複製其他電腦的 swap UUID、`resume_offset`、Kernel 開機參數或 PCI 裝置位址。第一次測試前，務必儲存工作並保留回退方式。

可以先查看 logind 回報的能力：

```bash
for feature in CanSuspend CanHibernate CanSuspendThenHibernate; do
  printf '%s: ' "$feature"
  busctl --system call org.freedesktop.login1 /org/freedesktop/login1 \
    org.freedesktop.login1.Manager "$feature"
done
```

QV9 實測回傳三項 `s "yes"`；但**能力回報 yes 不等於已證實 RTC 喚醒、Hibernate 映像寫入及 Resume 都會成功**。

### 2. 確認 Cinnamon 的現有設定與關蓋控制權

請在 Cinnamon 圖形桌面的終端機執行：

```bash
gsettings get org.cinnamon.SessionManager suspend-then-hibernate
gsettings get org.cinnamon.SessionManager prefer-hybrid-sleep
gsettings get org.cinnamon.settings-daemon.plugins.power inhibit-lid-switch
gsettings get org.cinnamon.settings-daemon.plugins.power lid-close-ac-action
gsettings get org.cinnamon.settings-daemon.plugins.power lid-close-battery-action
systemd-inhibit --list --no-pager
```

完成驗收時，QV9 的五項設定依序是 `true`、`false`、`true`、`'suspend'`、`'suspend'`。`systemd-inhibit` 顯示 `csd-power` 持有 `handle-lid-switch` inhibitor，代表平常由 Cinnamon 處理關蓋事件。

**不要只為了模仿 QV9 就切換 `inhibit-lid-switch`。** 我們在 Cinnamon 6.6.4 上觀察到，修改該值不會立刻釋放既有 inhibitor，需考慮桌面服務的啟動狀態。調整前先確認實際控制者，避免 Cinnamon 與 logind 同時處理關蓋。

### 3. 啟用 Cinnamon 原生 SuspendThenHibernate

確定手動休眠可恢復後，才在 Cinnamon Session 啟用：

```bash
gsettings set org.cinnamon.SessionManager prefer-hybrid-sleep false
gsettings set org.cinnamon.SessionManager suspend-then-hibernate true
```

QV9 的交流電及電池關蓋動作都設為 `suspend`，可以透過 Cinnamon 電源管理介面調整，也可以先用上一節的 `gsettings get` 查詢。請勿另外增加未協調的關蓋自動睡眠程式。

30 分鐘延遲使用 systemd 的 sleep drop-in，參考 [`examples/10-suspend-then-hibernate.conf`](examples/10-suspend-then-hibernate.conf)：

```ini
[Sleep]
HibernateDelaySec=30min
```

先檢查現有的 systemd 設定及版本，再決定是否採用。確認生效值：

```bash
systemd-analyze cat-config systemd/sleep.conf
```

[`examples/90-qv9-safe-suspend.conf`](examples/90-qv9-safe-suspend.conf) 是 QV9 使用的 logind 保守備援：`HandleLidSwitch=suspend`。**這個設定本身不會啟用自動 S4**；在 Cinnamon 持有關蓋控制權時，原生 SuspendThenHibernate 才由 Cinnamon 的設定決定。

### 4. 分階段實測，不要一開始就關蓋半小時

請接上交流電、儲存所有工作，並有人在電腦前：

1. **開蓋**執行一次短暫 Suspend／Resume。
2. 短暫關蓋再開蓋，確認鎖定畫面與正常恢復。
3. 最後才進行超過設定延遲時間的完整關蓋測試，確認真的進入 S4 並能恢復。

蒐集 systemd 服務及 Kernel 日誌：

```bash
journalctl -b -u systemd-suspend-then-hibernate.service --no-pager
journalctl -b -k --no-pager | grep -Ei 'PM: suspend|PM: hibernat|swsusp|resume'
```

**看到服務啟動不等於已經進入 S4。** 必須檢查實際 hibernation entry／exit 與恢復狀態。如果系統啟動了新的 boot，可用 `journalctl --list-boots` 找到應檢查的前一個 boot。其他症狀見[故障排除](docs/troubleshooting.md)。

## 選用：Python 關蓋鎖定 Handler

[`handler/lid-handler.py`](handler/lid-handler.py) 透過 D-Bus `PropertiesChanged` 監測 logind 的 `LidClosed` **屬性**，也訂閱 `PrepareForSleep` signal 與 Cinnamon ScreenSaver 狀態。

它的工作是關蓋時要求 ScreenSaver Lock，並追蹤鎖屏與睡眠狀態；**不呼叫 Suspend／Hibernate，也不持有 lid inhibitor**。Cinnamon 不需要這支 Python 程式才能使用原生 S4。

程式需要相容的 Cinnamon 桌面 Session、Python 3、PyGObject（`python3-gi`）。[`systemd/qv9-lid-handler.service`](systemd/qv9-lid-handler.service) 是使用者服務範例，假設程式位於 `~/.local/lib/qv9/lid-handler.py`，不是自動安裝腳本。

可執行不會觸發睡眠的 11 項離線測試：

```bash
python3 handler/test-stage-e1.py
```

## USB 喚醒、舊版腳本與限制

QV9 另有一份獨立的 xHCI USB 喚醒控制 hook，但**當時實際部署的 hook 原始碼尚未納入此儲存庫**。因此只提供[USB 喚醒觀察紀錄](docs/usb-wake.md)，不提供未經核對的替代程式。

`legacy/` 是早期登入與 fallback 腳本，沿用已不再作為正式設計的 ownership flock。它們保留供追溯，**不是啟用原生 S4 的必要元件**。詳見[舊版腳本說明](legacy/README.md)與[設計歷程](docs/development-notes.md)。

如果要停用 Cinnamon 原生自動 S4：

```bash
gsettings set org.cinnamon.SessionManager suspend-then-hibernate false
```

這不會修復其他休眠設定問題，詳見[安全與回退](docs/security-and-recovery.md)。

**尚未驗證的情境：**純電池長時間運作、Dock／外接顯示器、多次長期循環、Session 崩潰或其他機型。GitHub 適合備份公開原始碼及版本歷史，不能取代包含完整系統設定的私人離線備份。

本專案採用 [MIT License](LICENSE)。
