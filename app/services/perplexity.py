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
        Найди ВСЕХ ключевых публичных лиц компании "{company_name}" - людей которые представляют компанию:

        ПРИОРИТЕТНЫЕ ДОЛЖНОСТИ:
        1. Генеральный директор, CEO, Президент
        2. Коммерческий директор, Директор по продажам
        3. Финансовый директор, CFO
        4. IT-директор, CIO, CTO
        5. Директор по маркетингу, CMO
        6. Руководитель отдела продаж
        7. PR-директор, Директор по коммуникациям
        8. Основатель, Владелец (если публичный)

        ТАКЖЕ ИЩИ:
        - Людей выступающих на конференциях от компании
        - Авторов статей и интервью от лица компании
        - Спикеров в СМИ и соцсетях
        - Руководителей подразделений/филиалов

        Для каждого человека собери:
        - ФИО (полностью)
        - Должность
        - Email (если найдешь публично)
        - Телефон (если найдешь публично)
        - LinkedIn профиль (если есть)
        - TenChat профиль (если есть)
        - VK профиль (если есть)
        - Telegram (если найдешь)
        - Краткая справка (образование, достижения если есть)

        Верни ТОЛЬКО JSON без дополнительного текста:
        {{
            "executives": [
                {{
                    "name": "ФИО",
                    "position": "Должность",
                    "email": "email@company.ru",
                    "phone": "+7...",
                    "linkedin": "https://linkedin.com/in/...",
                    "tenchat": "https://tenchat.ru/...",
                    "vk": "https://vk.com/...",
                    "telegram": "@username",
                    "bio": "Краткая справка"
                }}
            ]
        }}

        Найди минимум 3-5 ключевых лиц, максимум 10.
        Если информация не найдена, используй null для полей.
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

        4. АКТИВНОСТЬ И РЕПУТАЦИЯ:
           - 5-7 последних значимых новостей (с датами и ссылками)
           - Участие в выставках/конференциях
           - Награды и достижения
           - Инвестиции (если были)
           - Партнерства

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
            "activity": {{
                "news": [
                    {{
                        "date": "YYYY-MM",
                        "title": "заголовок",
                        "source_url": "https://...",
                        "source_name": "название источника"
                    }}
                ],
                "events": ["выставки, конференции"],
                "awards": ["награды"],
                "investments": "...",
                "partnerships": ["партнеры"]
            }}
        }}

        ОСОБЕННО ВАЖНО найти оборот - проверь ВСЕ возможные источники!
        """

        return self._search(query, "Поиск финансов и бизнес-информации")

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
