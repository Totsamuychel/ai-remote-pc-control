# Telegram Remote Approvals Setup Guide

With the **Telegram Approval Bot**, you can safely authorize or reject sensitive AI actions (mouse clicks, shell commands, process termination) directly from your smartphone via interactive Telegram buttons.

---

## 1. Create Your Telegram Bot

1. Open Telegram and search for **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot`.
3. Give your bot a friendly name (e.g., `My Remote PC Approval Bot`) and a unique username ending in `bot` (e.g., `my_pc_approvals_bot`).
4. `@BotFather` will reply with your **Bot Token**:
   `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`

---

## 2. Obtain Your Telegram Chat ID

1. Open Telegram and search for **[@userinfobot](https://t.me/userinfobot)** or message your new bot and check `https://api.telegram.org/bot<TOKEN>/getUpdates`.
2. Note your numeric user ID (e.g., `987654321`).
3. Press **Start** (`/start`) in your newly created bot chat so the bot has permission to message you.

---

## 3. Configure AI Remote PC Control

Add your credentials to `.env`:

```env
TELEGRAM_BOT_TOKEN="1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ"
TELEGRAM_ALLOWED_CHAT_ID="987654321"
```

---

## 4. Run the Approval Bot Daemon

You can run the Telegram approval daemon concurrently with your server:

```bash
# In your terminal:
python agent/safety/telegram_bot.py
```

Or enable it as a background systemd user service.

---

## 5. How It Works in Practice

1. An AI agent invokes `click(x=500, y=300)` or `kill_process(pid=1234)`.
2. The MCP agent holds the request and generates a pending token `approval_id: "req-abc123xyz"`.
3. The Telegram bot instantly sends an alert to your phone:

```text
⚠️ AI Action Approval Required

Action: click
Details: {
  "x": 500,
  "y": 300,
  "button": "left"
}
Request ID: req-abc123xyz

[✅ Approve]   [❌ Reject]
```

4. When you tap **[✅ Approve]**:
   - The action is immediately executed on the remote PC.
   - The Telegram message updates to: `*✅ Approved*\nAction ID: req-abc123xyz`.
   - If someone else taps the button from another account, the request is rejected with `Unauthorized user`.
