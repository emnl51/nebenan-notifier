import requests


def send_message(bot_token, chat_id, text):
    if not bot_token or not chat_id:
        return False, "Telegram bot token veya chat_id eksik"
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={"chat_id": chat_id, "text": text, "disable_web_page_preview": False},
            timeout=15,
        )
        if resp.status_code == 200:
            return True, None
        return False, f"Telegram API hata: {resp.status_code} {resp.text}"
    except requests.RequestException as e:
        return False, str(e)


def test_connection(bot_token, chat_id):
    return send_message(bot_token, chat_id, "✅ Nebenan Notifier bağlantı testi başarılı.")
