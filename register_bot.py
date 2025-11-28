"""
Скрипт для регистрации бота в Битрикс24
Запускать локально после заполнения .env на сервере
"""
import requests
import sys

# НАСТРОЙКИ - УЖЕ ЗАПОЛНЕНЫ
BITRIX24_WEBHOOK_URL = "https://o2it.bitrix24.ru/rest/10/zd1pyk0n8xfspd4b/"
BOT_WEBHOOK_URL = "http://aistudy.dev.o2it.ru:8100/webhook/bitrix"

# Bot ID уже зарегистрирован: 74

def register_bot():
    """Регистрация бота в Битрикс24"""

    print("🤖 Регистрация Sales Scout бота в Битрикс24...")
    print(f"📍 Webhook URL бота: {BOT_WEBHOOK_URL}")

    # Параметры бота
    bot_data = {
        "CODE": "sales_scout",
        "TYPE": "B",
        "EVENT_MESSAGE_ADD": BOT_WEBHOOK_URL,
        "EVENT_WELCOME_MESSAGE": "Y",
        "PROPERTIES": {
            "NAME": "Sales Scout",
            "LAST_NAME": "Бот",
            "COLOR": "BLUE",
            "EMAIL": "bot@salesscout.ru",
            "PERSONAL_PHOTO": ""  # Можно добавить base64 encoded фото
        }
    }

    try:
        # Регистрируем бота
        url = f"{BITRIX24_WEBHOOK_URL}/imbot.register"
        response = requests.post(url, json=bot_data, timeout=30)
        response.raise_for_status()

        result = response.json()

        if result.get("result"):
            bot_id = result["result"]
            print("✅ Бот успешно зарегистрирован!")
            print(f"\n📋 BOT_ID: {bot_id}")
            print("\n" + "="*50)
            print("ВАЖНО! Добавьте BOT_ID в .env на сервере:")
            print("="*50)
            print(f"\nВыполните команду:\n")
            print(f'ssh myserver "sed -i \'s/BITRIX24_BOT_ID=/BITRIX24_BOT_ID={bot_id}/\' /opt/sales-scout/.env && systemctl restart sales-scout.service"')
            print("\nИли вручную:")
            print(f"1. ssh myserver")
            print(f"2. nano /opt/sales-scout/.env")
            print(f"3. Установите BITRIX24_BOT_ID={bot_id}")
            print(f"4. Ctrl+X, Y, Enter")
            print(f"5. systemctl restart sales-scout.service")

        else:
            print("❌ Ошибка регистрации бота:")
            print(result)
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к Битрикс24: {e}")
        print("\nПроверьте:")
        print("1. BITRIX24_WEBHOOK_URL правильный")
        print("2. У вебхука есть права на imbot")
        print("3. Интернет соединение работает")
        sys.exit(1)


def check_bot_status():
    """Проверка что бот зарегистрирован"""
    try:
        url = f"{BITRIX24_WEBHOOK_URL}/imbot.bot.list"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        bots = response.json().get("result", [])
        sales_scout = [b for b in bots if b.get("CODE") == "sales_scout"]

        if sales_scout:
            print("\n✅ Бот Sales Scout найден в системе:")
            bot = sales_scout[0]
            print(f"BOT_ID: {bot['ID']}")
            print(f"Имя: {bot['NAME']} {bot['LAST_NAME']}")
            return True
        else:
            print("\n⚠️ Бот Sales Scout не найден в системе")
            return False

    except Exception as e:
        print(f"\n⚠️ Не удалось проверить статус бота: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("  РЕГИСТРАЦИЯ SALES SCOUT БОТА В БИТРИКС24")
    print("="*60)

    # Проверяем заполнены ли настройки
    if "ваш-портал" in BITRIX24_WEBHOOK_URL or "ваш_webhook" in BITRIX24_WEBHOOK_URL:
        print("\n❌ ОШИБКА: Заполните BITRIX24_WEBHOOK_URL в скрипте!")
        print("Откройте register_bot.py и укажите реальный webhook URL")
        sys.exit(1)

    print(f"\n📡 Битрикс24: {BITRIX24_WEBHOOK_URL.split('/rest/')[0]}")
    print(f"🌐 Bot Server: {BOT_WEBHOOK_URL}\n")

    # Проверяем не зарегистрирован ли уже бот
    print("Проверка существующих ботов...")
    already_registered = check_bot_status()

    if already_registered:
        answer = input("\nБот уже зарегистрирован. Зарегистрировать заново? (yes/no): ")
        if answer.lower() != "yes":
            print("Регистрация отменена.")
            sys.exit(0)

    # Регистрируем бота
    register_bot()
