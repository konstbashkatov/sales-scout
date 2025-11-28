"""
Perplexity сервис для поиска информации о компаниях через OpenRouter
"""
import requests
import json
import logging
from typing import Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class PerplexityService:
    """Сервис для работы с Perplexity через OpenRouter API"""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.perplexity_model = "perplexity/sonar-pro"

    def find_company_with_inn(self, query: str) -> Dict:
        """
        Поиск компании по названию/ИНН и получение ИНН

        Args:
            query: Название компании или ИНН

        Returns:
            Словарь с найденными вариантами компаний
        """
        search_query = f"""
        Найди РОССИЙСКУЮ компанию или ИП по запросу: "{query}"

        ВАЖНО: Ищи ТОЛЬКО в российских источниках (сайты .ru, российские соцсети, российские базы данных)

        Если это ИНН (10 или 12 цифр) - найди компанию по этому ИНН в российских реестрах.
        Если это название - найди компанию работающую в России. Используй:
        - Официальные сайты компаний
        - ВКонтакте, Telegram
        - Российские базы данных компаний
        - Яндекс поиск

        Верни ТОЛЬКО JSON без дополнительного текста:
        {{
            "found": true,
            "variants": [
                {{
                    "name": "Полное название компании или ИП",
                    "short_name": "Краткое коммерческое название",
                    "inn": "ИНН (10 или 12 цифр, обязательно!)",
                    "confidence": 0.95,
                    "description": "Краткое описание деятельности"
                }}
            ]
        }}

        Если найдено несколько компаний - верни топ-5 самых релевантных.
        Если точное совпадение - верни только его.
        ОБЯЗАТЕЛЬНО укажи ИНН для каждого варианта!
        """

        return self._search(search_query, "Поиск компании и ИНН")

    def find_online_presence(self, company_name: str, inn: Optional[str] = None) -> Dict:
        """
        Поиск онлайн-присутствия компании (сайт, соцсети)

        Args:
            company_name: Название компании
            inn: ИНН компании (опционально, для точности)

        Returns:
            Словарь с найденными ссылками
        """
        inn_part = f" (ИНН: {inn})" if inn else ""
        query = f"""
        Найди онлайн-присутствие российской компании {company_name}{inn_part}:

        1. Официальный сайт (полный URL)
        2. Страница ВКонтакте (полный URL)
        3. Telegram канал или бот (полный URL, формат t.me/...)
        4. YouTube канал (полный URL)
        5. Другие социальные сети (если есть)

        Верни ТОЛЬКО JSON без дополнительного текста в формате:
        {{
            "website": "https://...",
            "vk": "https://vk.com/...",
            "telegram": "https://t.me/...",
            "youtube": "https://youtube.com/...",
            "other": ["https://..."]
        }}

        Если что-то не найдено, используй null.
        """

        return self._search(query, "Поиск онлайн-присутствия")

    def find_executives(self, company_name: str) -> Dict:
        """
        Поиск информации о руководителях и ключевых публичных лицах компании

        Args:
            company_name: Название компании

        Returns:
            Словарь с информацией о руководителях и ключевых лицах
        """
        query = f"""
        Найди ключевых лиц компании "{company_name}" через поиск в следующих источниках:

        ГДЕ ИСКАТЬ (в порядке приоритета):

        1. TENCHAT (tenchat.ru) - ОБЯЗАТЕЛЬНО ПРОВЕРЬ:
           - Поиск по названию компании в TenChat
           - Поиск сотрудников компании в профилях
           - Авторы постов от лица компании
           - URL формат: https://tenchat.ru/имя_пользователя

        2. LINKEDIN (linkedin.com) - ОБЯЗАТЕЛЬНО ПРОВЕРЬ:
           - Страница компании на LinkedIn: linkedin.com/company/{company_name}
           - Раздел "Сотрудники" на странице компании
           - Поиск людей с указанием этой компании в профиле
           - URL формат: https://linkedin.com/in/имя_пользователя

        3. TELEGRAM - ОБЯЗАТЕЛЬНО ПРОВЕРЬ:
           - Личные каналы сотрудников компании
           - Упоминания в тематических чатах
           - Авторские каналы руководителей
           - URL формат: https://t.me/username или @username

        4. ДОПОЛНИТЕЛЬНЫЕ ИСТОЧНИКИ:
           - VC.ru - авторы статей от компании
           - Habr - авторы от компании
           - YouTube - спикеры от компании
           - Конференции и вебинары - спикеры
           - Пресс-релизы и новости - упоминаемые лица
           - Сайт компании - раздел "Команда" или "О нас"

        КОГО ИСКАТЬ:
        - Генеральный директор, CEO, Основатель
        - Коммерческий директор, Директор по продажам
        - Директор по маркетингу, PR-директор
        - Технический директор, CTO
        - Публичные спикеры и эксперты компании

        Верни ТОЛЬКО JSON:
        {{
            "executives": [
                {{
                    "name": "ФИО полностью",
                    "position": "Должность",
                    "tenchat": "https://tenchat.ru/...",
                    "linkedin": "https://linkedin.com/in/...",
                    "telegram": "@username или https://t.me/...",
                    "vk": "https://vk.com/...",
                    "email": "email@company.ru",
                    "phone": "+7...",
                    "source": "где найден (TenChat/LinkedIn/Telegram/сайт компании)"
                }}
            ]
        }}

        ВАЖНО: Приоритет - найти профили в TenChat, LinkedIn и Telegram!
        Найди 3-7 ключевых лиц. Если данных нет - используй null.
        """

        return self._search(query, "Поиск ключевых лиц компании")

    def deep_search_person(self, person_name: str, company_name: str, position: str = None) -> Dict:
        """
        Глубокий поиск информации о конкретном человеке

        Args:
            person_name: ФИО человека
            company_name: Название компании
            position: Должность (опционально)

        Returns:
            Детальная информация о человеке
        """
        position_part = f" ({position})" if position else ""
        query = f"""
        Найди МАКСИМАЛЬНО ДЕТАЛЬНУЮ информацию о человеке: {person_name}{position_part} из компании "{company_name}"

        ЛИЧНЫЕ КОНТАКТЫ И ПРОФИЛИ:
        1. Рабочий email
        2. Личный email (если публичный)
        3. Рабочий телефон
        4. Личный телефон (если публичен)
        5. LinkedIn профиль (полный URL)
        6. TenChat профиль
        7. VK профиль (личная страница)
        8. Facebook профиль
        9. Instagram (если связан с бизнесом)
        10. Telegram username

        ПУБЛИЧНАЯ АКТИВНОСТЬ:
        11. Личный блог или сайт
        12. Статьи на VC.ru
        13. Публикации на Habr
        14. Статьи на Medium
        15. Канал на YouTube
        16. Подкасты (если есть)
        17. Профиль на Forbes/РБК
        18. Другие публичные площадки

        ПРОФЕССИОНАЛЬНАЯ ИНФОРМАЦИЯ:
        19. Образование (университет, специальность)
        20. Предыдущий опыт работы
        21. Достижения и награды
        22. Выступления на конференциях
        23. Интервью в СМИ (ссылки)
        24. Цитаты и высказывания
        25. Области экспертизы

        Верни ТОЛЬКО JSON без дополнительного текста:
        {{
            "person": {{
                "name": "ФИО",
                "position": "должность",
                "company": "компания"
            }},
            "contacts": {{
                "work_email": "...",
                "personal_email": "...",
                "work_phone": "...",
                "personal_phone": "..."
            }},
            "social_profiles": {{
                "linkedin": "https://...",
                "tenchat": "https://...",
                "vk": "https://...",
                "facebook": "https://...",
                "instagram": "https://...",
                "telegram": "@..."
            }},
            "content_platforms": {{
                "personal_blog": "https://...",
                "vc_ru": "https://vc.ru/u/...",
                "habr": "https://habr.com/ru/users/...",
                "medium": "https://medium.com/@...",
                "youtube": "https://youtube.com/...",
                "podcasts": ["ссылки на подкасты"]
            }},
            "publications": [
                {{
                    "title": "Название статьи/интервью",
                    "url": "https://...",
                    "platform": "VC.ru/Forbes/РБК/...",
                    "date": "YYYY-MM"
                }}
            ],
            "professional": {{
                "education": "университет, специальность",
                "previous_experience": ["предыдущие компании"],
                "achievements": ["награды, достижения"],
                "expertise": ["области экспертизы"],
                "speaking": ["конференции где выступал"]
            }},
            "bio_summary": "Краткая биография (2-3 предложения)"
        }}

        Если информация не найдена - используй null.
        ОЧЕНЬ ВАЖНО найти хотя бы один способ связи (email/телефон/соцсеть)!
        """

        return self._search(query, f"Детальный поиск о {person_name}")

    def find_business_info(self, company_name: str, inn: Optional[str] = None) -> Dict:
        """
        Поиск детальной бизнес-информации о компании (оборот, финансы, деятельность)

        Args:
            company_name: Название компании
            inn: ИНН компании (опционально)

        Returns:
            Словарь с бизнес-информацией
        """
        inn_part = f" (ИНН: {inn})" if inn else ""
        query = f"""
        Найди МАКСИМАЛЬНО ДЕТАЛЬНУЮ бизнес-информацию о компании "{company_name}"{inn_part}:

        1. ФИНАНСЫ И МАСШТАБ (ОЧЕНЬ ВАЖНО):
           - Годовой оборот/выручка в рублях (поищи в:)
             * Финансовых отчетах
             * Интервью руководителей
             * Новостях о компании
             * Рейтингах и топах
             * Данных о закупках/контрактах
           - Месячный оборот (если найдешь)
           - Динамика за последние годы (2023, 2024, 2025)
           - Прибыль (если есть публичные данные)
           - Количество сотрудников (точное или примерное)
           - Размер компании (малый/средний/крупный бизнес)

        2. ДЕЯТЕЛЬНОСТЬ:
           - Основные продукты или услуги (детальный список)
           - Целевая аудитория (B2B, B2C, B2G)
           - Основные/крупнейшие клиенты
           - Отрасль и сегмент рынка
           - География работы (регионы, страны)
           - Доля рынка (если известна)

        3. ТЕХНОЛОГИИ:
           - Какую CRM систему используют
           - Какую ERP систему используют
           - Системы автоматизации
           - Технологический стек (для IT-компаний)
           - Упоминания о цифровой трансформации

        4. КОНКУРЕНТЫ И РЫНОК:
           - Основные конкуренты (3-5 компаний)
           - Позиционирование на рынке
           - Конкурентные преимущества
           - Инвестиции (если были)
           - Партнерства и интеграции

        Верни ТОЛЬКО JSON без дополнительного текста:
        {{
            "finances": {{
                "revenue_yearly_rub": "число или диапазон",
                "revenue_monthly_rub": "...",
                "revenue_source": "откуда данные",
                "revenue_year": "2024",
                "profit": "...",
                "employees_count": "число или диапазон",
                "company_size": "малый/средний/крупный",
                "growth_trend": "растет/стабильно/падает",
                "growth_percentage": "..."
            }},
            "business": {{
                "products": ["список продуктов/услуг"],
                "target_audience": "B2B/B2C/B2G",
                "major_clients": ["список клиентов"],
                "industry": "отрасль",
                "geography": ["регионы работы"],
                "market_share": "..."
            }},
            "technologies": {{
                "crm": "название CRM",
                "erp": "название ERP",
                "automation": ["другие системы"],
                "tech_stack": ["технологии"]
            }},
            "market": {{
                "competitors": ["список конкурентов"],
                "positioning": "позиционирование",
                "competitive_advantages": ["преимущества"],
                "investments": "информация об инвестициях",
                "partnerships": ["партнеры"]
            }}
        }}

        ОСОБЕННО ВАЖНО найти оборот - проверь ВСЕ возможные источники!
        """

        return self._search(query, "Поиск финансов и бизнес-информации")

    def find_news_and_events(self, company_name: str, inn: Optional[str] = None, industry: Optional[str] = None) -> Dict:
        """
        Поиск новостей о компании и участия в отраслевых мероприятиях

        Args:
            company_name: Название компании
            inn: ИНН компании (опционально)
            industry: Отрасль компании (опционально, для поиска отраслевых мероприятий)

        Returns:
            Словарь с новостями и мероприятиями
        """
        from datetime import datetime, timedelta

        # Вычисляем точные даты для поиска
        today = datetime.now()
        six_months_ago = today - timedelta(days=180)
        six_months_ahead = today + timedelta(days=180)

        date_from = six_months_ago.strftime("%Y-%m-%d")
        date_to_past = today.strftime("%Y-%m-%d")
        date_to_future = six_months_ahead.strftime("%Y-%m-%d")

        inn_part = f" (ИНН: {inn})" if inn else ""
        industry_part = f" Отрасль: {industry}." if industry else ""

        query = f"""
        Найди ВСЕ новости и мероприятия компании "{company_name}"{inn_part}.{industry_part}

        ВАЖНО - ТОЧНЫЕ ВРЕМЕННЫЕ РАМКИ:
        • Сегодняшняя дата: {date_to_past}
        • Новости: с {date_from} по {date_to_past} (последние 6 месяцев)
        • Прошедшие мероприятия: с {date_from} по {date_to_past} (последние 6 месяцев)
        • Предстоящие мероприятия: с {date_to_past} по {date_to_future} (следующие 6 месяцев)

        ГДЕ ИСКАТЬ НОВОСТИ (проверь ВСЕ источники):

        1. ДЕЛОВЫЕ СМИ:
           - РБК (rbc.ru) - поиск по названию компании
           - Коммерсантъ (kommersant.ru)
           - Ведомости (vedomosti.ru)
           - Forbes Russia (forbes.ru)
           - Inc Russia (incrussia.ru)
           - Деловой Петербург (dp.ru)
           - The Bell (thebell.io)

        2. ТЕХНОЛОГИЧЕСКИЕ И БИЗНЕС-ИЗДАНИЯ:
           - VC.ru - статьи и новости
           - Habr - если IT-компания
           - CNews, TAdviser - если IT/технологии
           - Retail.ru - если ритейл
           - Другие отраслевые издания

        3. ИНФОРМАГЕНТСТВА:
           - ТАСС (tass.ru)
           - Интерфакс (interfax.ru)
           - РИА Новости (ria.ru)
           - Прайм (1prime.ru)

        4. ПРЕСС-РЕЛИЗЫ:
           - Сайт компании (раздел "Новости" или "Пресс-центр")
           - PR-службы и агрегаторы пресс-релизов

        ГДЕ ИСКАТЬ МЕРОПРИЯТИЯ:

        1. ВЫСТАВКИ И ЭКСПОЗИЦИИ:
           - Expocentr.ru (Экспоцентр Москва)
           - Expoforum.ru (Экспофорум СПб)
           - Crocus-expo.ru (Крокус Экспо)
           - Отраслевые выставки (поиск по отрасли компании)
           - Региональные выставочные центры

        2. КОНФЕРЕНЦИИ И ФОРУМЫ:
           - ПМЭФ, ВЭФ и другие крупные форумы
           - Отраслевые конференции
           - Бизнес-форумы
           - Профессиональные саммиты

        3. НАГРАДЫ И РЕЙТИНГИ:
           - Рейтинги РБК, Forbes, Коммерсантъ
           - Отраслевые премии
           - Бизнес-награды

        Верни ТОЛЬКО JSON:
        {{
            "news": [
                {{
                    "date": "YYYY-MM-DD",
                    "title": "Заголовок новости",
                    "summary": "Краткое содержание (2-3 предложения)",
                    "source": "Название издания",
                    "url": "https://полная_ссылка",
                    "type": "новость/интервью/пресс-релиз/аналитика",
                    "sentiment": "позитивная/нейтральная/негативная"
                }}
            ],
            "exhibitions": [
                {{
                    "date": "YYYY-MM",
                    "name": "Название выставки",
                    "location": "Место проведения",
                    "role": "экспонент/посетитель/спонсор",
                    "booth_info": "информация о стенде если есть",
                    "url": "ссылка на информацию"
                }}
            ],
            "conferences": [
                {{
                    "date": "YYYY-MM",
                    "name": "Название конференции/форума",
                    "location": "Место",
                    "role": "спикер/участник/спонсор/организатор",
                    "speakers": ["ФИО спикеров от компании"],
                    "topic": "тема выступления если известна",
                    "url": "ссылка"
                }}
            ],
            "awards": [
                {{
                    "date": "YYYY",
                    "name": "Название награды/рейтинга",
                    "position": "место в рейтинге или номинация",
                    "organizer": "кто присудил",
                    "url": "ссылка"
                }}
            ],
            "upcoming_events": [
                {{
                    "date": "YYYY-MM",
                    "name": "Название предстоящего мероприятия",
                    "type": "выставка/конференция/форум",
                    "url": "ссылка"
                }}
            ],
            "media_activity_score": "высокая/средняя/низкая",
            "total_mentions_estimate": "примерное количество упоминаний в СМИ"
        }}

        СТРОГО СОБЛЮДАЙ ВРЕМЕННЫЕ РАМКИ:
        - Новости ТОЛЬКО с {date_from} по {date_to_past}
        - Прошедшие мероприятия ТОЛЬКО с {date_from} по {date_to_past}
        - Предстоящие мероприятия ТОЛЬКО с {date_to_past} по {date_to_future}
        - НЕ включай события старше 6 месяцев!
        - Минимум 5-10 новостей если компания активная
        - Укажи ВСЕ найденные выставки и конференции
        - Обязательно укажи ссылки на источники
        """

        return self._search(query, "Поиск новостей и мероприятий")

    def _search(self, query: str, search_type: str) -> Dict:
        """
        Выполнение поискового запроса через Perplexity (OpenRouter)

        Args:
            query: Текст запроса
            search_type: Тип поиска (для логирования)

        Returns:
            Распарсенный JSON ответ
        """
        payload = {
            "model": self.perplexity_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты - эксперт по поиску информации о российских компаниях. Возвращай ТОЛЬКО валидный JSON, без markdown форматирования, без дополнительного текста. Используй актуальные данные из интернета. Фокусируйся на российских источниках."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.2,
            "max_tokens": 3000
        }

        try:
            logger.info(f"{search_type}: отправка запроса к Perplexity через OpenRouter")

            response = requests.post(
                self.base_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=90  # Perplexity через OpenRouter может работать дольше
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # OpenRouter может предоставлять дополнительную информацию
            usage = data.get("usage", {})

            logger.info(f"{search_type}: получен ответ от Perplexity")
            logger.debug(f"Использование токенов: {usage}")

            # Парсим JSON из ответа
            try:
                # Убираем markdown форматирование если есть
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                result = json.loads(content)
                result["_usage"] = usage  # Добавляем информацию об использовании токенов
                return result

            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON от Perplexity: {e}")
                logger.error(f"Полученный контент: {content}")
                # Возвращаем сырой ответ в случае ошибки
                return {
                    "raw_response": content,
                    "_usage": usage,
                    "_error": "JSON parsing failed"
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к Perplexity через OpenRouter: {e}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка в Perplexity сервисе: {e}")
            raise


# Глобальный экземпляр сервиса
perplexity_service = PerplexityService()
