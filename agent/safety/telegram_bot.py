#!/usr/bin/env python3
"""Telegram Approval Bot Integration for AI Remote PC Control.

Allows administrators to remotely approve or reject pending AI actions
(such as mouse clicks, terminal execution, file overwrites) via interactive
Telegram Inline Keyboard buttons directly from their smartphone.
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
import urllib.parse
import urllib.request
from typing import Dict, Optional, Set

from agent.safety.approvals import ApprovalManager

logger = logging.getLogger("telegram_approvals")


class TelegramApprovalNotifier:
    """Manages Telegram bot notifications and interactive callbacks for action approvals."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        poll_interval: float = 2.0,
    ):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_ALLOWED_CHAT_ID", "")
        self.poll_interval = poll_interval
        self.manager = ApprovalManager.get_instance()
        self._notified_ids: Set[str] = set()
        self._message_id_map: Dict[str, int] = {}  # approval_id -> telegram message_id
        self._last_update_id = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def is_configured(self) -> bool:
        """Check if Telegram credentials are provided."""
        return bool(self.bot_token and self.chat_id)

    def _api_request(self, method: str, data: Optional[dict] = None) -> Optional[dict]:
        """Send HTTP POST request to Telegram Bot API."""
        if not self.is_configured:
            return None

        url = f"https://api.telegram.org/bot{self.bot_token}/{method}"
        try:
            headers = {"Content-Type": "application/json"}
            payload = json.dumps(data or {}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Telegram API error ({method}): {e}")
            return None

    def send_approval_prompt(self, approval_id: str, action: str, details: dict) -> bool:
        """Send an interactive approval message with Approve/Reject inline buttons."""
        if not self.is_configured:
            return False

        text = (
            f"⚠️ *AI Action Approval Required*\n\n"
            f"*Action:* `{action}`\n"
            f"*Details:* ```json\n{json.dumps(details, indent=2)}\n```\n"
            f"*Request ID:* `{approval_id}`"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"approve:{approval_id}"},
                    {"text": "❌ Reject", "callback_data": f"reject:{approval_id}"},
                ]
            ]
        }

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup,
        }

        res = self._api_request("sendMessage", payload)
        if res and res.get("ok"):
            msg_id = res["result"]["message_id"]
            self._message_id_map[approval_id] = msg_id
            self._notified_ids.add(approval_id)
            return True
        return False

    def handle_updates(self):
        """Poll and handle button clicks from Telegram."""
        if not self.is_configured:
            return

        payload = {
            "offset": self._last_update_id + 1,
            "timeout": 5,
            "allowed_updates": ["callback_query"],
        }
        res = self._api_request("getUpdates", payload)
        if not res or not res.get("ok"):
            return

        for update in res.get("result", []):
            self._last_update_id = update["update_id"]
            if "callback_query" not in update:
                continue

            query = update["callback_query"]
            query_id = query["id"]
            from_id = str(query.get("from", {}).get("id", ""))
            data = query.get("data", "")

            # Security verification: Only accept callbacks from the authorized chat ID
            if self.chat_id and from_id != str(self.chat_id):
                self._api_request("answerCallbackQuery", {
                    "callback_query_id": query_id,
                    "text": "Unauthorized user",
                    "show_alert": True
                })
                continue

            if ":" in data:
                action, approval_id = data.split(":", 1)
                success = False
                if action == "approve":
                    success = self.manager.approve(approval_id)
                    feedback = "✅ Approved" if success else "Approval failed or expired"
                elif action == "reject":
                    success = self.manager.reject(approval_id)
                    feedback = "❌ Rejected" if success else "Rejection failed or expired"
                else:
                    feedback = "Unknown action"

                # Acknowledge button click
                self._api_request("answerCallbackQuery", {
                    "callback_query_id": query_id,
                    "text": feedback,
                })

                # Update message to reflect final decision
                msg_id = query.get("message", {}).get("message_id")
                if msg_id:
                    self._api_request("editMessageText", {
                        "chat_id": self.chat_id,
                        "message_id": msg_id,
                        "text": f"*{feedback}*\nAction ID: `{approval_id}`",
                        "parse_mode": "Markdown",
                    })

    def poll_pending_approvals(self):
        """Inspect ApprovalManager and dispatch notifications for new requests."""
        pending = self.manager.get_pending_requests()
        for req in pending:
            if req.id not in self._notified_ids:
                self.send_approval_prompt(req.id, req.action, req.details)

    def _loop(self):
        """Background execution loop."""
        while self._running:
            try:
                self.poll_pending_approvals()
                self.handle_updates()
            except Exception as e:
                logger.error(f"Error in Telegram loop: {e}")
            time.sleep(self.poll_interval)

    def start(self):
        """Start the Telegram polling loop in a background daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Telegram Approval Notifier started.")

    def stop(self):
        """Stop the background polling loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    notifier = TelegramApprovalNotifier()
    if not notifier.is_configured:
        print("[!] TELEGRAM_BOT_TOKEN or TELEGRAM_ALLOWED_CHAT_ID not configured.")
        print("    Set them in .env or run with: TELEGRAM_BOT_TOKEN=... TELEGRAM_ALLOWED_CHAT_ID=... python telegram_bot.py")
        sys.exit(1)

    print("[*] Starting Telegram Approval Bot daemon...")
    notifier.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        notifier.stop()
