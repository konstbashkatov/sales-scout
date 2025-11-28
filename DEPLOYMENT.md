# Инструкция по развертыванию Sales Scout на myserver

## Статус развертывания

✅ **Развернуто успешно на сервере aistudy.dev.o2it.ru**

### Детали развертывания:

- **Сервер**: aistudy.dev.o2it.ru
- **Директория**: `/opt/sales-scout`
- **Порт**: `8100`
- **Systemd сервис**: `sales-scout.service`
- **Python**: 3.10.12 (виртуальное окружение)
- **Статус**: Запущен и работает

## URL для доступа

### API Endpoints

- **Главная**: http://aistudy.dev.o2it.ru:8100/
- **Health check**: http://aistudy.dev.o2it.ru:8100/health
- **Статистика**: http://aistudy.dev.o2it.ru:8100/stats
- **Webhook (для Битрикс24)**: http://aistudy.dev.o2it.ru:8100/webhook/bitrix

## Следующие шаги

### 1. Заполните API ключи

Подключитесь к серверу и отредактируйте `.env`:

```bash
ssh myserver
nano /opt/sales-scout/.env
```

Заполните следующие параметры:

```env
# Bitrix24
BITRIX24_WEBHOOK_URL=https://ваш-портал.bitrix24.ru/rest/1/ваш_код
BITRIX24_BOT_ID=

# DaData (получить на https://dadata.ru/)
DADATA_API_KEY=ваш_реальный_ключ

# Perplexity (получить на https://www.perplexity.ai/)
PERPLEXITY_API_KEY=ваш_реальный_ключ

# OpenRouter (ваш существующий ключ)
OPENROUTER_API_KEY=ваш_реальный_ключ

# Опционально: измените модель или описание продукта
DEFAULT_MODEL=anthropic/claude-3.5-sonnet
OUR_PRODUCT_DESCRIPTION=Ваше описание продукта
```

После изменения перезапустите сервис:

```bash
systemctl restart sales-scout.service
```

### 2. Зарегистрируйте бота в Битрикс24

Создайте скрипт `register_bot.py` на локальной машине:

```python
import requests

webhook_url = "https://ваш-портал.bitrix24.ru/rest/1/ваш_код"
bot_webhook_url = "http://aistudy.dev.o2it.ru:8100/webhook/bitrix"

response = requests.post(f"{webhook_url}/imbot.register", json={
    "CODE": "sales_scout",
    "TYPE": "B",
    "EVENT_MESSAGE_ADD": bot_webhook_url,
    "EVENT_WELCOME_MESSAGE": "Y",
    "PROPERTIES": {
        "NAME": "Sales Scout",
        "LAST_NAME": "Бот",
        "COLOR": "BLUE",
        "EMAIL": "bot@salesscout.ru"
    }
})

result = response.json()
if result.get("result"):
    print(f"Бот успешно зарегистрирован!")
    print(f"BOT_ID: {result['result']}")
    print(f"\nДобавьте BOT_ID в .env на сервере:")
    print(f"BITRIX24_BOT_ID={result['result']}")
else:
    print(f"Ошибка: {result}")
```

Запустите и скопируйте BOT_ID в `.env` на сервере.

### 3. Проверьте работу

```bash
# Проверка статуса сервиса
ssh myserver systemctl status sales-scout.service

# Просмотр логов
ssh myserver tail -f /opt/sales-scout/sales_scout.log

# Проверка API
curl http://aistudy.dev.o2it.ru:8100/health
```

## Управление сервисом

### Команды systemd

```bash
# Запуск
ssh myserver systemctl start sales-scout.service

# Остановка
ssh myserver systemctl stop sales-scout.service

# Перезапуск
ssh myserver systemctl restart sales-scout.service

# Статус
ssh myserver systemctl status sales-scout.service

# Просмотр логов
ssh myserver journalctl -u sales-scout.service -f

# Или логи приложения
ssh myserver tail -f /opt/sales-scout/sales_scout.log
```

### Обновление кода

Если нужно обновить код:

```bash
# На локальной машине (из директории проекта)
cd "/Users/konstantin/Sales scout"
tar -czf /tmp/sales-scout.tar.gz --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' --exclude='*.log' .
scp /tmp/sales-scout.tar.gz myserver:/tmp/

# На сервере
ssh myserver "cd /opt/sales-scout && systemctl stop sales-scout.service && tar -xzf /tmp/sales-scout.tar.gz && rm /tmp/sales-scout.tar.gz && systemctl start sales-scout.service"
```

## Изоляция от других проектов

Sales Scout полностью изолирован:

✅ **Отдельная директория**: `/opt/sales-scout` (не пересекается с `/opt/ai-platform`, `/opt/web`, `/opt/mcp-gateway`)
✅ **Отдельное виртуальное окружение**: Python зависимости изолированы
✅ **Отдельный порт**: 8100 (не конфликтует с другими сервисами)
✅ **Отдельный systemd сервис**: независимый запуск/остановка
✅ **Отдельные логи**: `/opt/sales-scout/sales_scout.log`

## Безопасность

### Файрвол

Убедитесь что порт 8100 открыт для входящих соединений:

```bash
ssh myserver "ufw allow 8100/tcp || iptables -A INPUT -p tcp --dport 8100 -j ACCEPT"
```

### HTTPS (опционально, для production)

Для HTTPS нужно настроить reverse proxy через nginx или получить прямой SSL сертификат.

Пока для MVP можно использовать HTTP.

## Мониторинг

### Проверка работоспособности

```bash
# Автоматическая проверка каждые 5 минут
watch -n 300 "curl -s http://aistudy.dev.o2it.ru:8100/health"
```

### Статистика использования

```bash
# Просмотр статистики оценок
curl http://aistudy.dev.o2it.ru:8100/stats

# Просмотр лога оценок
ssh myserver cat /opt/sales-scout/feedback_log.jsonl
```

## Troubleshooting

### Сервис не запускается

```bash
# Проверить логи systemd
ssh myserver journalctl -u sales-scout.service -n 50

# Проверить логи приложения
ssh myserver cat /opt/sales-scout/sales_scout.log

# Проверить .env
ssh myserver cat /opt/sales-scout/.env
```

### Ошибки конфигурации

```bash
# Проверить что все API ключи заполнены
ssh myserver "cd /opt/sales-scout && source venv/bin/activate && python -c 'from app.config import settings; print(settings.dict())'"
```

### Большое потребление ресурсов

```bash
# Проверить использование памяти и CPU
ssh myserver "ps aux | grep uvicorn"
ssh myserver "systemctl status sales-scout.service"
```

## Backup и восстановление

### Резервное копирование

```bash
# Бэкап всего проекта
ssh myserver "tar -czf /tmp/sales-scout-backup-$(date +%Y%m%d).tar.gz /opt/sales-scout"
scp myserver:/tmp/sales-scout-backup-*.tar.gz ./backups/
```

### Восстановление

```bash
# Остановить сервис
ssh myserver systemctl stop sales-scout.service

# Восстановить из бэкапа
scp ./backups/sales-scout-backup-YYYYMMDD.tar.gz myserver:/tmp/
ssh myserver "cd / && tar -xzf /tmp/sales-scout-backup-YYYYMMDD.tar.gz"

# Запустить сервис
ssh myserver systemctl start sales-scout.service
```

## Масштабирование

Если потребуется больше производительности:

### 1. Увеличить количество workers

Отредактируйте `/etc/systemd/system/sales-scout.service`:

```ini
ExecStart=/opt/sales-scout/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8100 --workers 4
```

### 2. Настроить nginx load balancer

Запустить несколько экземпляров на разных портах (8100, 8101, 8102...)

### 3. Добавить Redis для кэширования

Установить Redis и использовать для кэширования результатов поиска.

## Контакты и поддержка

При проблемах проверьте:
1. Логи: `/opt/sales-scout/sales_scout.log`
2. Systemd: `journalctl -u sales-scout.service`
3. API ключи в `.env`

---

**Развертывание завершено!** 🚀

Webhook URL для Битрикс24: `http://aistudy.dev.o2it.ru:8100/webhook/bitrix`
