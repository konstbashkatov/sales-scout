# Sales Scout - Простой вебхук (одна строка)

## 🎯 URL для вебхука Битрикс24:

```
http://aistudy.dev.o2it.ru:8100/webhook/research
```

---

## 📝 Синтаксис (всё в одну строку):

### Пример 1: С названием компании

```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Document:TITLE}}&userId={{=Document:ASSIGNED_BY_ID}}
```

### Пример 2: С ИНН

```
http://aistudy.dev.o2it.ru:8100/webhook/research?inn={{=Document:UF_CRM_INN}}&userId={{=Document:ASSIGNED_BY_ID}}
```

### Пример 3: Название + ИНН (для точности)

```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Document:TITLE}}&inn={{=Document:UF_CRM_INN}}&userId={{=Document:ASSIGNED_BY_ID}}
```

---

## 🔧 Настройка в Битрикс24:

### В автоматизации CRM (роботы):

1. Откройте: CRM → Сделки/Контакты → Настроить → Автоматизация
2. Добавьте робота: **"Webhook"**
3. Заполните:
   - **URL:** `http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Document:TITLE}}&userId={{=Document:ASSIGNED_BY_ID}}`
   - **Метод:** GET (или оставьте по умолчанию)
4. Сохраните

**Готово!** Теперь при срабатывании робота - пользователю придет досье.

### В бизнес-процессе:

1. Откройте: CRM → Бизнес-процессы
2. Добавьте активность: **"HTTP-запрос"**
3. Заполните:
   - **URL:** `http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Document:TITLE}}&userId={{=Document:ASSIGNED_BY_ID}}`
   - **Метод:** GET
4. Сохраните

---

## 📋 Параметры URL:

| Параметр | Описание | Пример | Обязательный |
|----------|----------|--------|--------------|
| `companyName` | Название компании | `Яндекс` | Нет* |
| `inn` | ИНН компании | `7707083893` | Нет* |
| `userId` | ID пользователя Битрикс24 | `10` | **Да** |

*Хотя бы один: `companyName` или `inn`

---

## 🧪 Примеры для тестирования:

### Тест 1: Яндекс

```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName=Яндекс&userId=10
```

### Тест 2: Сбербанк по ИНН

```
http://aistudy.dev.o2it.ru:8100/webhook/research?inn=7736207543&userId=10
```

### Тест 3: Idol face

```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName=Idol%20face&userId=10
```

*(пробелы кодируются как %20)*

---

## 💡 Использование с переменными Битрикс24:

### Из сделки (Deal):

```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Document:COMPANY_TITLE}}&userId={{=Document:ASSIGNED_BY_ID}}
```

### Из контакта (Contact):

```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Contact:COMPANY_TITLE}}&inn={{=Contact:UF_CRM_INN}}&userId={{=Contact:ASSIGNED_BY_ID}}
```

### Из компании (Company):

```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Company:TITLE}}&inn={{=Company:UF_CRM_INN}}&userId={{=CurrentUser:ID}}
```

### Из лида (Lead):

```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Lead:COMPANY_TITLE}}&userId={{=Lead:ASSIGNED_BY_ID}}
```

---

## 📊 Что происходит:

1. **Битрикс24 вызывает URL** → Sales Scout получает запрос
2. **Моментальный ответ** → `{"status":"ok","message":"..."}`
3. **Обработка в фоне** → 1-3 минуты
4. **Результат пользователю** → Досье приходит в чат Битрикс24

---

## ✅ Быстрая проверка (откройте в браузере):

```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName=Яндекс&userId=10
```

Должны увидеть:
```json
{
    "status": "ok",
    "message": "Исследование компании 'Яндекс' запущено"
}
```

А пользователю 10 в Битрикс24 через 1-2 минуты придет досье!

---

## 🎯 Готовая строка для копирования:

**Для автоматизации сделок:**
```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Document:COMPANY_TITLE}}&userId={{=Document:ASSIGNED_BY_ID}}
```

**Для автоматизации контактов:**
```
http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Document:TITLE}}&userId={{=Document:ASSIGNED_BY_ID}}
```

Просто скопируйте и вставьте в настройки вебхука! 🚀
