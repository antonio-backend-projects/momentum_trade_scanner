import requests

def send_telegram(token: str, chat_id: str, text: str):
    if not token or not chat_id:
        return
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat_id, "text": text}, timeout=10)
    if r.status_code >= 300:
        try:
            print("Telegram error:", r.json())
        except Exception:
            print("Telegram error:", r.text)
