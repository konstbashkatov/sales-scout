#!/usr/bin/env python3
"""
Скрипт для обновления обработчика событий бота в Битрикс24
"""
import requests

# НАСТРОЙКИ
BITRIX24_WEBHOOK_URL = "https://o2it.bitrix24.ru/rest/10/zd1pyk0n8xfspd4b"
BOT_ID = "74"
BOT_WEBHOOK_URL = "http://aistudy.dev.o2it.ru:8100/webhook/bitrix"

def update_bot_handler():
    """Обновление обработчика событий бота"""

    print("="*60)
    print("  ОБНОВЛЕНИЕ ОБРАБОТЧИКА SALES SCOUT БОТА")
    print("="*60)
    print(f"\nBOT_ID: {BOT_ID}")
    print(f"Webhook URL: {BOT_WEBHOOK_URL}\n")

    # Обновляем обработчик
    url = f"{BITRIX24_WEBHOOK_URL}/imbot.update"

    payload = {
        "BOT_ID": BOT_ID,
        "PROPERTIES": {
            "EVENT_MESSAGE_ADD": BOT_WEBHOOK_URL
        }
    }

    try:
        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()

        result = response.json()

        if result.get("result"):
            print("✅ Обработчик успешно обновлен!")
            print(f"\nТеперь бот будет получать сообщения на:")
            print(f"  {BOT_WEBHOOK_URL}")
            print("\n" + "="*60)
            print("  ГОТОВО! Попробуйте написать боту в Битрикс24")
            print("="*60)
            print("\nПримеры сообщений:")
            print("  • Яндекс")
            print("  • 7707083893")
            print("  • ООО Рога и Копыта")
            return True
        else:
            print("❌ Ошибка при обновлении бота:")
            print(f"  {result}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к Битрикс24: {e}")
        return False

if __name__ == "__main__":
    success = update_bot_handler()
    exit(0 if success else 1)
