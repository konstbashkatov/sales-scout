"""
LangChain анализатор для создания досье компании с рекомендациями по продажам
"""
import logging
import json
from typing import Dict
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from app.config import settings
from app.services.dadata import dadata_service
from app.services.perplexity import perplexity_service
from app.services.website_parser import website_parser

logger = logging.getLogger(__name__)


class SalesAnalyzer:
    """Анализатор для создания досье компании"""

    def __init__(self):
        self.llm = self._init_llm()

    def _init_llm(self) -> ChatOpenAI:
        """Инициализация LLM через OpenRouter"""
        return ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=settings.OPENROUTER_API_KEY,
            temperature=0.3,
            max_tokens=4000
        )

    async def create_company_dossier(self, inn: str = None, company_name: str = None, company_website: str = None) -> str:
        """
        Создание полного досье компании с рекомендациями по продажам

        НОВАЯ ЛОГИКА: Сначала Perplexity (интернет), потом DaData (обогащение)

        Args:
            inn: ИНН компании (опционально)
            company_name: Название компании (опционально)
            company_website: Сайт компании (опционально, если известен заранее)

        Returns:
            Отформатированное досье в виде текста
        """
        if not inn and not company_name and not company_website:
            return "❌ Укажите ИНН, название компании или сайт"

        query = inn or company_name or company_website
        logger.info(f"Начало создания досье для: {query}, сайт: {company_website}")

        # =================================================================
        # ЭТАП 1: ИДЕНТИФИКАЦИЯ КОМПАНИИ
        # Цель: получить ТОЧНЫЕ данные - название, ИНН, сайт
        # Эти данные будут использоваться во ВСЕХ последующих запросах
        # =================================================================

        confirmed_name = None      # Подтвержденное название компании
        confirmed_inn = inn        # Подтвержденный ИНН
        confirmed_website = company_website  # Подтвержденный сайт
        egrul_data = None

        # ШАГ 1.1: Если есть сайт - парсим его для получения юр. данных
        if company_website:
            try:
                logger.info("Шаг 1.1: Извлечение юридической информации с сайта")
                legal_info = website_parser.extract_legal_info(company_website)

                if legal_info.get("inn"):
                    confirmed_inn = legal_info["inn"]
                    logger.info(f"ИНН с сайта: {confirmed_inn}")

                if legal_info.get("company_name"):
                    confirmed_name = legal_info["company_name"]
                    logger.info(f"Название компании с сайта: {confirmed_name}")
            except Exception as e:
                logger.warning(f"Ошибка извлечения юридической информации с сайта: {e}")

        # ШАГ 1.2: Если есть ИНН - получаем данные из ЕГРЮЛ (DaData)
        if confirmed_inn:
            try:
                logger.info("Шаг 1.2: Получение данных из ЕГРЮЛ (DaData)")
                egrul_data = dadata_service.find_company_by_inn(confirmed_inn)

                if egrul_data:
                    # ЕГРЮЛ - официальный источник, его данные приоритетны
                    confirmed_name = egrul_data["short_name"] or egrul_data["full_name"]
                    logger.info(f"ЕГРЮЛ подтвердил: {confirmed_name}")
            except Exception as e:
                logger.error(f"Ошибка получения данных из DaData: {e}")

        # ШАГ 1.3: Если нет ИНН - ищем компанию через Perplexity
        if not confirmed_inn and (company_name or company_website):
            try:
                search_query = company_name or company_website
                logger.info(f"Шаг 1.3: Поиск компании через Perplexity: {search_query}")
                company_search = perplexity_service.find_company_with_inn(search_query)

                if company_search.get("found") and company_search.get("variants"):
                    first_variant = company_search["variants"][0]
                    confirmed_inn = first_variant.get("inn")
                    if not confirmed_name:
                        confirmed_name = first_variant.get("short_name") or first_variant.get("name")
                    # Также получаем сайт если его нет
                    if not confirmed_website and first_variant.get("website"):
                        confirmed_website = first_variant["website"]

                    logger.info(f"Perplexity нашел: {confirmed_name}, ИНН: {confirmed_inn}")

                    # Теперь подтверждаем через ЕГРЮЛ
                    if confirmed_inn and not egrul_data:
                        try:
                            egrul_data = dadata_service.find_company_by_inn(confirmed_inn)
                            if egrul_data:
                                confirmed_name = egrul_data["short_name"] or egrul_data["full_name"]
                                logger.info(f"ЕГРЮЛ подтвердил: {confirmed_name}")
                        except Exception as e:
                            logger.error(f"Ошибка подтверждения через DaData: {e}")
            except Exception as e:
                logger.error(f"Ошибка поиска через Perplexity: {e}")

        # ШАГ 1.4: Если ИНН есть, но название не найдено - пробуем Perplexity по ИНН
        if confirmed_inn and not confirmed_name:
            try:
                logger.info("Шаг 1.4: Поиск названия по ИНН через Perplexity")
                company_search = perplexity_service.find_company_with_inn(confirmed_inn)

                if company_search.get("found") and company_search.get("variants"):
                    first_variant = company_search["variants"][0]
                    confirmed_name = first_variant.get("short_name") or first_variant.get("name")
                    if not confirmed_website and first_variant.get("website"):
                        confirmed_website = first_variant["website"]
                    logger.info(f"Perplexity нашел по ИНН: {confirmed_name}")
            except Exception as e:
                logger.error(f"Ошибка поиска через Perplexity по ИНН: {e}")

        # Финальная проверка - должно быть хотя бы название
        if not confirmed_name:
            # Используем исходное название как fallback
            confirmed_name = company_name

        if not confirmed_name:
            return f"""😔 К сожалению, не удалось найти компанию "{query}"

Попробуйте:
• Использовать более точное название
• Указать ИНН (10 или 12 цифр)
• Попробовать английское название (если международная компания)"""

        # =================================================================
        # ЭТАП 2: СБОР ИНФОРМАЦИИ О ПОДТВЕРЖДЕННОЙ КОМПАНИИ
        # Используем confirmed_name, confirmed_inn, confirmed_website
        # =================================================================

        logger.info(f"=== КОМПАНИЯ ИДЕНТИФИЦИРОВАНА ===")
        logger.info(f"Название: {confirmed_name}")
        logger.info(f"ИНН: {confirmed_inn}")
        logger.info(f"Сайт: {confirmed_website}")
        logger.info(f"=================================")

        # ШАГ 2.1: ПОИСК ОНЛАЙН-ПРИСУТСТВИЯ (если сайт еще не известен)
        logger.info("Шаг 2/5: Поиск сайта и соцсетей")
        online_presence = {}
        if not confirmed_website:
            online_presence = perplexity_service.find_online_presence(confirmed_name, confirmed_inn)
            if online_presence.get("website"):
                confirmed_website = online_presence["website"]
                logger.info(f"Найден сайт: {confirmed_website}")
        else:
            online_presence = {"website": confirmed_website}

        # ШАГ 2.2: ПАРСИНГ КОНТАКТОВ С САЙТА
        logger.info("Шаг 3/5: Парсинг контактов с сайта")
        website_contacts = {}
        website_legal_info = {}
        if confirmed_website:
            website_contacts = website_parser.parse_contacts(confirmed_website)
            website_legal_info = website_parser.extract_legal_info(confirmed_website)
            if website_legal_info:
                logger.info(f"Юридическая информация с сайта: {website_legal_info}")

        # ШАГ 2.3: ПОИСК ЛПР И БИЗНЕС-ИНФОРМАЦИИ
        logger.info("Шаг 4/5: Поиск ЛПР и бизнес-информации (Perplexity)")
        # ВАЖНО: используем confirmed_name и confirmed_inn для консистентности
        executives_data = perplexity_service.find_executives(confirmed_name)
        business_info = perplexity_service.find_business_info(confirmed_name, confirmed_inn)

        # ШАГ 2.4: ПОИСК НОВОСТЕЙ И МЕРОПРИЯТИЙ
        logger.info("Шаг 5/5: Поиск новостей и мероприятий (Perplexity)")
        # Определяем отрасль для более точного поиска мероприятий
        industry = None
        if business_info and business_info.get("business"):
            industry = business_info["business"].get("industry")
        # ВАЖНО: используем confirmed_name и confirmed_inn
        news_and_events = perplexity_service.find_news_and_events(confirmed_name, confirmed_inn, industry)

        # Агрегируем все данные
        aggregated_data = {
            "egrul": egrul_data,
            "online_presence": online_presence,
            "website_contacts": website_contacts,
            "website_legal_info": website_legal_info,
            "executives": executives_data,
            "business_info": business_info,
            "news_and_events": news_and_events,
            "confirmed_company": {
                "name": confirmed_name,
                "inn": confirmed_inn,
                "website": confirmed_website
            }
        }

        logger.info("Генерация итогового досье с помощью LLM")

        # Генерируем досье с помощью LLM
        dossier = self._generate_dossier_with_llm(aggregated_data)

        return dossier

    def _generate_dossier_with_llm(self, data: Dict) -> str:
        """
        Генерация досье с использованием LLM

        Args:
            data: Агрегированные данные о компании

        Returns:
            Отформатированное досье
        """
        # Формируем промпт для LLM
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(data)

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = self.llm.invoke(messages)
            dossier = response.content

            return dossier

        except Exception as e:
            logger.error(f"Ошибка при генерации досье: {e}")
            # Fallback: возвращаем базовое досье без LLM анализа
            return self._generate_fallback_dossier(data)

    def _get_system_prompt(self) -> str:
        """Системный промпт для LLM"""
        return f"""Ты - эксперт по B2B продажам с 15-летним опытом.

Твоя задача: создать детальное досье компании для менеджера по продажам.

Наш продукт: {settings.OUR_PRODUCT_DESCRIPTION}

Цель досье: помочь менеджеру выбрать правильную тактику продаж и подготовиться к контакту с компанией.

ВАЖНО:
- Будь конкретным и практичным
- Фокусируйся на действиях, а не общих фразах
- Указывай конкретные рекомендации по подходу
- Учитывай размер бизнеса при рекомендациях
- Выделяй ключевые точки входа и контакты

ФОРМАТИРОВАНИЕ ССЫЛОК (Битрикс24 BB-code):
- Все URL делай кликабельными: [URL=https://example.com]Текст ссылки[/URL]
- Email: [URL=mailto:email@company.ru]email@company.ru[/URL]
- Профили соцсетей: [URL=https://vk.com/company]VK[/URL]
- Telegram: [URL=https://t.me/channel]@channel[/URL]

Формат ответа - структурированное досье с эмодзи для наглядности и кликабельными ссылками."""

    def _get_user_prompt(self, data: Dict) -> str:
        """Промпт с данными о компании"""
        data_json = json.dumps(data, ensure_ascii=False, indent=2)

        return f"""Создай досье компании на основе собранных данных:

{data_json}

Используй следующий формат:

═══════════════════════════════════
📋 ДОСЬЕ КОМПАНИИ

🏢 [НАЗВАНИЕ]
📍 [Адрес]
👤 Директор: [ФИО]
✅ Статус: [Статус] с [Дата регистрации]

═══════════════════════════════════

📊 МАСШТАБ БИЗНЕСА
💰 Оборот: [примерный оборот если найден]
👥 Сотрудников: [примерное количество]
📈 Динамика: [Растет/Стабильно/Падает - твоя оценка]
🏆 Категория: [Малый/Средний/Крупный бизнес]

═══════════════════════════════════

🌐 ОНЛАЙН-ПРИСУТСТВИЕ
• Сайт: [URL=https://example.com]example.com[/URL]
• VK: [URL=https://vk.com/company]vk.com/company[/URL]
• Telegram: [URL=https://t.me/channel]@channel[/URL]
• YouTube: [URL=https://youtube.com/...]YouTube[/URL]

📞 Телефоны:
• [телефон 1]
• [телефон 2]

📧 Email:
• [URL=mailto:email@company.ru]email@company.ru[/URL]

═══════════════════════════════════

👥 КЛЮЧЕВЫЕ ЛИЦА (публичные представители)

[Для каждого найденного руководителя/публичного лица:]
[N]️⃣ [ФИО] - [Должность]
   📧 [URL=mailto:email@company.ru]email@company.ru[/URL]
   📱 [телефон если найден]
   🔗 LinkedIn: [URL=https://linkedin.com/in/...]профиль[/URL]
   🔗 TenChat: [URL=https://tenchat.ru/...]профиль[/URL]
   🔗 VK: [URL=https://vk.com/...]профиль[/URL]
   💬 Telegram: [URL=https://t.me/username]@username[/URL]
   📝 [Краткая справка о человеке если есть]

[Если не найдены ЛПР, укажи директора из ЕГРЮЛ]

═══════════════════════════════════

💼 ЧЕМ ЗАНИМАЮТСЯ
[Описание деятельности на основе ОКВЭД и найденной информации]

Основные продукты/услуги:
• [список если найдено]

Целевая аудитория: [B2B/B2C/B2G]

═══════════════════════════════════

💻 ТЕХНОЛОГИИ
[Если найдена информация об используемых технологиях:]
• CRM: [название или "неизвестно"]
• ERP: [название или "неизвестно"]
• Другое: [список]

[Если нет данных: "Информация о технологиях не найдена"]

═══════════════════════════════════

📰 ПОСЛЕДНИЕ НОВОСТИ
[Из news_and_events.news - список 5-7 последних с кликабельными ссылками:]
• [Дата]: [Краткое описание] - [URL=https://source.ru]источник[/URL]
• [Дата]: [Краткое описание] - [URL=https://source.ru]источник[/URL]

[Если нет: "Новости не найдены"]

═══════════════════════════════════

🎪 ВЫСТАВКИ И МЕРОПРИЯТИЯ
[Из news_and_events.exhibitions и news_and_events.conferences]

📍 Выставки:
[Если есть выставки:]
• [Дата]: [Название выставки] ([роль: экспонент/посетитель]) - [URL=https://...]ссылка[/URL]

🎤 Конференции и форумы:
[Если есть конференции:]
• [Дата]: [Название] - спикер: [ФИО] - [URL=https://...]ссылка[/URL]

🏆 Награды и рейтинги:
[Из news_and_events.awards:]
• [Год]: [Название награды/рейтинга] - [позиция] - [URL=https://...]ссылка[/URL]

📅 Предстоящие мероприятия:
[Из news_and_events.upcoming_events:]
• [Дата]: [Название] ([тип]) - [URL=https://...]ссылка[/URL]

[Если нет данных: "Информация о мероприятиях не найдена"]

Медиа-активность: [news_and_events.media_activity_score]

═══════════════════════════════════

🎯 ВАЖНО ДЛЯ ПРОДАЖИ

📌 НА ЧТО СДЕЛАТЬ АКЦЕНТ:
• [Боль 1: что наш продукт может решить для такой компании]
• [Боль 2]
• [Боль 3]

⚠️ ЧТО УЧЕСТЬ:
• [Особенность 1: что важно знать о компании]
• [Особенность 2: возможные возражения]
• [Особенность 3: на что обратить внимание]

═══════════════════════════════════

Используй найденные данные для персонализации рекомендаций."""

    def _generate_fallback_dossier(self, data: Dict) -> str:
        """Запасной вариант досье без LLM (если API недоступен)"""
        egrul = data["egrul"]
        online = data["online_presence"]
        contacts = data["website_contacts"]

        dossier = f"""📋 ДОСЬЕ КОМПАНИИ

🏢 {egrul["short_name"] or egrul["full_name"]}
📍 {egrul["address"]["full"]}
👤 Директор: {egrul["director"]["name"]} ({egrul["director"]["post"]})
✅ Статус: {egrul["status"]}

═══════════════════════════════════

🌐 ОНЛАЙН-ПРИСУТСТВИЕ
• Сайт: {online.get("website") or "не найден"}
• VK: {online.get("vk") or "не найден"}
• Telegram: {online.get("telegram") or "не найден"}

📞 Телефоны: {", ".join(contacts.get("phones", [])) or "не найдены"}
📧 Email: {", ".join(contacts.get("emails", [])) or "не найдены"}

═══════════════════════════════════

ℹ️ Полный анализ временно недоступен.
Используйте найденные контакты для связи с компанией."""

        return dossier


# Глобальный экземпляр анализатора
sales_analyzer = SalesAnalyzer()
