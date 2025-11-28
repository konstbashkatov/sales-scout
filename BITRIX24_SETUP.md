# Настройка чат-бота Sales Scout в Битрикс24

## Вариант 1: Настройка существующего бота (BOT_ID=74)

### Если бот уже создан, обновите его обработчик:

```bash
curl -X POST "https://o2it.bitrix24.ru/rest/10/zd1pyk0n8xfspd4b/imbot.update" \
  -d "BOT_ID=74" \
  -d "PROPERTIES[EVENT_MESSAGE_ADD]=http://aistudy.dev.o2it.ru:8100/webhook/bitrix"
```

Или через Python:

```python
import requests

url = "https://o2it.bitrix24.ru/rest/10/zd1pyk0n8xfspd4b/imbot.update"
data = {
    "BOT_ID": "74",
    "PROPERTIES": {
        "EVENT_MESSAGE_ADD": "http://aistudy.dev.o2it.ru:8100/webhook/bitrix"
    }
}

response = requests.post(url, json=data)
print(response.json())
```

---

## Вариант 2: Создать нового бота с нуля

### Через API (рекомендуется):

```bash
curl -X POST "https://o2it.bitrix24.ru/rest/10/zd1pyk0n8xfspd4b/imbot.register" \
  -H "Content-Type: application/json" \
  -d '{
    "CODE": "sales_scout",
    "TYPE": "B",
    "EVENT_MESSAGE_ADD": "http://aistudy.dev.o2it.ru:8100/webhook/bitrix",
    "EVENT_WELCOME_MESSAGE": "Y",
    "PROPERTIES": {
      "NAME": "Sales Scout",
      "LAST_NAME": "Бот",
      "COLOR": "BLUE",
      "EMAIL": "bot@salesscout.ru"
    }
  }'
```

### Через готовый скрипт:

Используйте `update_bot.py`:

```python
import requests

webhook_url = "https://o2it.bitrix24.ru/rest/10/zd1pyk0n8xfspd4b"
bot_webhook = "http://aistudy.dev.o2it.ru:8100/webhook/bitrix"

# Обновление существующего бота
response = requests.post(f"{webhook_url}/imbot.update", data={
    "BOT_ID": "74",
    "PROPERTIES": {
        "EVENT_MESSAGE_ADD": bot_webhook
    }
})

print("Результат:", response.json())

if response.json().get("result"):
    print("✅ Бот успешно обновлен!")
    print(f"Обработчик установлен: {bot_webhook}")
else:
    print("❌ Ошибка:", response.json())
```

---

## Вариант 3: Через интерфейс Битрикс24 (если есть доступ)

### Если у вас есть права администратора:

1. Откройте Битрикс24: https://o2it.bitrix24.ru/
2. Перейдите: **Приложения** → **Разработчикам** → **Другое** → **Чат-боты**
3. Найдите бота "Sales Scout" (ID: 74)
4. Нажмите **Изменить**
5. В поле **"Обработчик при получении сообщения"** укажите:
   ```
   http://aistudy.dev.o2it.ru:8100/webhook/bitrix
   ```
6. Сохраните

---

## Проверка настройки

### После настройки проверьте:

```bash
# Проверка что бот зарегистрирован
curl "https://o2it.bitrix24.ru/rest/10/zd1pyk0n8xfspd4b/imbot.bot.list"
```

### Тестирование:

1. Найдите бота "Sales Scout" в чатах Битрикс24
2. Напишите: `тест`
3. Проверьте логи:

```bash
ssh myserver "tail -f /opt/sales-scout/sales_scout.log"
```

Вы должны увидеть:
```
INFO - Получен webhook от Битрикс24, Content-Type: ...
INFO - Получено сообщение из диалога XXX: тест
```

---

## Ключевые параметры

| Параметр | Значение |
|----------|----------|
| **Webhook URL** | `http://aistudy.dev.o2it.ru:8100/webhook/bitrix` |
| **BOT_ID** | `74` |
| **Битрикс24 API** | `https://o2it.bitrix24.ru/rest/10/zd1pyk0n8xfspd4b/` |

---

## Быстрое решение (копируйте и выполните):

```bash
# Создайте файл update_bot.py
cat > update_bot.py << 'EOF'
import requests

webhook_url = "https://o2it.bitrix24.ru/rest/10/zd1pyk0n8xfspd4b"
bot_webhook = "http://aistudy.dev.o2it.ru:8100/webhook/bitrix"

# Обновление бота
response = requests.post(f"{webhook_url}/imbot.update", data={
    "BOT_ID": "74",
    "PROPERTIES": {
        "EVENT_MESSAGE_ADD": bot_webhook
    }
})

result = response.json()
print("Результат:", result)

if result.get("result"):
    print("\n✅ Бот успешно обновлен!")
    print(f"Обработчик: {bot_webhook}")
else:
    print(f"\n❌ Ошибка: {result.get('error_description', result)}")
EOF

# Выполните
python update_bot.py
```

---

## Отладка

Если бот все еще не отвечает после настройки:

```bash
# Мониторинг логов в реальном времени
ssh myserver "tail -f /opt/sales-scout/sales_scout.log"

# Напишите боту "тест"
# В логах должно появиться сообщение о получении webhook
```

---

## ЧТО УКАЗАТЬ В БИТРИКС24:

**Обработчик сообщений (EVENT_MESSAGE_ADD):**
```
http://aistudy.dev.o2it.ru:8100/webhook/bitrix
```

Только этот URL! Больше ничего не нужно.
