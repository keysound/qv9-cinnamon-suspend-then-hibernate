# QV9 Linux Mint Cinnamon：關蓋 Suspend → 30 分鐘後 S4

這是 Panasonic Let's note QV9 的**實機成功案例與參考原始碼**，
不是適用於所有 Linux 筆電的自動休眠安裝器。

## 核心觀念：我們沒有自己寫一套 S4

真正執行睡眠的是 **Cinnamon 原生電源策略 + systemd**：

1. 關蓋後，Cinnamon 使用 `suspend` 動作。
2. `org.cinnamon.SessionManager suspend-then-hibernate=true` 使 Cinnamon
   優先呼叫 logind 的 `SuspendThenHibernate`。
3. systemd 使用 `HibernateDelaySec=30min`，先進入 s2idle 再嘗試 S4。
4. `handler/lid-handler.py` 只輔助觸發 PIN 鎖定、觀察事件與防止錯誤狀態，
   **不負責發動 S4，不持有 lid inhibitor**。

> **重要：** `suspend-then-hibernate=true` 影響 Cinnamon 執行的其他
> Suspend，不是只有關蓋。未確認 S4 正常以前，不要貿然啟用。

## 已驗收的環境與結果

- QV9、Linux Mint 22.3 Cinnamon。
- `cinnamon-settings-daemon 6.6.4`、`cinnamon-session 6.6.3`、
  `Cinnamon 6.6.9`、`systemd 255`。
- Kernel 7.0.0-38-generic；原本已完成「手動 S4／resume」所需的
  swapfile、kernel resume 相關配置。
- Cinnamon：`inhibit-lid-switch=true`；
  `lid-close-ac-action='suspend'`；
  `lid-close-battery-action='suspend'`；
  `prefer-hybrid-sleep=false`；
  `suspend-then-hibernate=true`。
- systemd：`HibernateDelaySec=30min`；logind
  `HandleLidSwitch=suspend` 作為備援策略。
- 2026-10-23 23:13:52 關蓋進入 s2idle；23:43:53 自動轉 S4；
  2026-10-24 00:04:52 恢復。開蓋直接 Resume，看到 PIN，
  原有視窗保留，無二次 Suspend。
- 2026-10-24 00:30 重開機後設定保留，Handler v0.8.4-e1 自動啟動。
- 成功的是一次完整 30 分鐘 S4 驗收加上短時間循環，
  **未驗證純電池、Docked、多螢幕或長期耐久性**。

## 正式修改設定前的唯讀查核

先確認自己的電腦已能**手動進入 Hibernate 並成功 Resume**。
不同裝置的 UUID、swapfile resume_offset 和開機參數都不相同，
**絕對不要複製別人的 `resume=UUID` 或 `resume_offset`**。

```bash
busctl --system call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager CanSuspendThenHibernate
gsettings get org.cinnamon.SessionManager suspend-then-hibernate
gsettings get org.cinnamon.SessionManager prefer-hybrid-sleep
gsettings get org.cinnamon.settings-daemon.plugins.power inhibit-lid-switch
gsettings get org.cinnamon.settings-daemon.plugins.power lid-close-ac-action
gsettings get org.cinnamon.settings-daemon.plugins.power lid-close-battery-action
systemd-analyze cat-config systemd/logind.conf
systemd-analyze cat-config systemd/sleep.conf
systemd-inhibit --list
```

測試 QV9 的設定範例放在 `examples/`。務必先理解裝置上
Cinnamon 和 logind 誰負責關蓋，別一股腦套用。

需要停止 Cinnamon 原生的 SuspendThenHibernate 時：

```bash
gsettings set org.cinnamon.SessionManager suspend-then-hibernate false
```

## 程式碼範圍

- `handler/lid-handler.py`：經 QV9 部署的 v0.8.4-e1。
- `handler/test-stage-e1.py`：11 個離線回歸測試，不會真的 Suspend。
- `systemd/`：對應 systemd 使用者服務的參考設定。
- `examples/`：參考 sleep 與 logind drop-in 設定。
- `legacy/`：過去的登入與 fallback 程式，保留供備份及研究，
  **不建議未經審查直接安裝**。
- `docs/usb-wake.md`：原系統另有 xHCI wake hook，但目前尚未收錄其
  實際驗收的程式全文。PCI 位址 `0000:00:14.0` 僅適用於已核對的 QV9。

需要自行複製或調整電源腳本的人，建議先下載 GitHub 原始碼、
確認本機配置並保留安全回退手段。這不是一鍵安裝包。

## 備份與授權

GitHub 可保存公開原始碼與版本歷史，**不應拿來備份內含個人、
主機識別或敏感資訊的完整系統快照**；另外保留可還原的私人備份。

MIT 授權。未保證適用所有硬體。
