import httpx
import os

def invia_notifica_realtime(messaggio: str):
    webhook_url = os.getenv("CEO_ALERT_WEBHOOK")  # Es: Slack, Telegram, WhatsApp API
    if webhook_url:
        httpx.post(webhook_url, json={"text": messaggio}) 