from typing import Any, Dict, List, Optional
from loguru import logger
from curl_cffi import requests

from config.settings import settings


class TelegramAlerter:
    """
    Modular Telegram Bot Notifier for high-discount deals and price drops.
    Operates in Mock / Simulation mode if tokens are not configured in .env.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        min_discount: Optional[float] = None
    ):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.min_discount = min_discount if min_discount is not None else settings.ALERT_MIN_DISCOUNT_PERCENT

    @property
    def is_configured(self) -> bool:
        """Returns True if both bot token and chat ID are provided."""
        return bool(self.bot_token and self.chat_id)

    def format_deal_message(self, deal: Dict[str, Any]) -> str:
        """Formats deal into a clean Telegram HTML message."""
        name = deal.get("name", "Unknown Product")
        brand = deal.get("brand", "ASOS")
        curr_price = deal.get("current_price", 0.0)
        prev_price = deal.get("previous_price", 0.0)
        disc = deal.get("discount_percent", 0.0)
        currency = deal.get("currency", "EUR")
        url = deal.get("url", "https://www.asos.com")

        old_price_str = f"<s>{prev_price:.2f} {currency}</s>" if prev_price else "N/A"

        return (
            f"🔥 <b>ASOS Price Drop Alert!</b>\n\n"
            f"🛍 <b>{name}</b>\n"
            f"🏷 <b>Brand:</b> {brand}\n"
            f"📉 <b>Discount:</b> <code>-{disc:.1f}%</code>\n"
            f"💰 <b>Price:</b> <b>{curr_price:.2f} {currency}</b> (Old: {old_price_str})\n\n"
            f"🔗 <a href=\"{url}\">Open on ASOS</a>"
        )

    def send_alert(self, deal: Dict[str, Any]) -> bool:
        """
        Sends an alert for a single deal.
        In Mock mode (no credentials), logs the simulated notification and returns True.
        """
        message = self.format_deal_message(deal)

        if not self.is_configured:
            logger.info(
                f"[Telegram Alert (Simulated)] Deal: {deal.get('name')} | "
                f"-{deal.get('discount_percent', 0):.1f}% | "
                f"{deal.get('current_price')} {deal.get('currency')} | "
                f"(Telegram tokens not configured in .env - running in mock mode)"
            )
            return True

        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        try:
            resp = requests.post(endpoint, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info(f"Telegram alert successfully sent for: {deal.get('name')}")
                return True
            else:
                logger.error(f"Failed to send Telegram alert: HTTP {resp.status_code} - {resp.text}")
                return False
        except Exception as exc:
            logger.error(f"Error communicating with Telegram Bot API: {exc}")
            return False

    def notify_deals(self, deals: List[Dict[str, Any]], threshold: Optional[float] = None) -> int:
        """
        Iterates through deals, filtering those with discount >= threshold,
        and dispatches alert notifications. Returns count of dispatched alerts.
        """
        target_threshold = threshold if threshold is not None else self.min_discount
        qualifying_deals = [
            d for d in deals
            if (d.get("discount_percent") or 0.0) >= target_threshold
        ]

        logger.info(
            f"Evaluating alerts: {len(qualifying_deals)} deals exceed threshold (-{target_threshold:.1f}%)."
        )

        sent_count = 0
        for deal in qualifying_deals:
            if self.send_alert(deal):
                sent_count += 1

        return sent_count
