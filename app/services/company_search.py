"""
Сервис поиска компаний с возможностью выбора из нескольких вариантов
"""
import logging
from typing import Dict, List, Optional, Tuple

from app.services.perplexity import perplexity_service
from app.services.dadata import dadata_service

logger = logging.getLogger(__name__)


class CompanySearchService:
    """Сервис для интеллектуального поиска компаний"""

    async def search_company(self, query: str) -> Tuple[str, Optional[str], Optional[List[Dict]]]:
        """
        Поиск компании по запросу (название или ИНН)

        Args:
            query: Запрос пользователя (название или ИНН)

        Returns:
            Кортеж (статус, инн, варианты):
            - статус: "found_one", "found_multiple", "not_found", "error"
            - инн: ИНН найденной компании (если статус "found_one")
            - варианты: Список вариантов (если статус "found_multiple")
        """
        logger.info(f"Начало поиска компании: {query}")

        # Шаг 1: Ищем через Perplexity (быстрый поиск с ИНН)
        try:
            logger.info("Поиск компании через Perplexity...")
            perplexity_result = perplexity_service.find_company_with_inn(query)

            if not perplexity_result.get("found"):
                logger.warning("Perplexity не нашел компанию")
                return ("not_found", None, None)

            variants = perplexity_result.get("variants", [])

            if not variants:
                return ("not_found", None, None)

            # Если найден только один вариант с высокой уверенностью
            if len(variants) == 1:
                company = variants[0]
                inn = company.get("inn")

                if inn:
                    logger.info(f"Найдена компания: {company.get('name')} (ИНН: {inn})")
                    return ("found_one", inn, None)
                else:
                    logger.warning("ИНН не найден в результатах Perplexity")
                    return ("not_found", None, None)

            # Если найдено несколько вариантов
            if len(variants) > 1:
                logger.info(f"Найдено {len(variants)} вариантов компаний")
                # Фильтруем варианты с ИНН
                variants_with_inn = [v for v in variants if v.get("inn")]

                if not variants_with_inn:
                    logger.warning("Ни у одного варианта нет ИНН")
                    return ("not_found", None, None)

                return ("found_multiple", None, variants_with_inn)

        except Exception as e:
            logger.error(f"Ошибка при поиске через Perplexity: {e}")
            # Если Perplexity не сработал - пробуем DaData
            pass

        # Шаг 2: Fallback на DaData (если Perplexity не сработал)
        try:
            logger.info("Fallback: поиск через DaData...")

            # Проверяем не ИНН ли это
            if query.isdigit() and len(query) in [10, 12]:
                egrul_data = dadata_service.find_company_by_inn(query)
                if egrul_data:
                    return ("found_one", egrul_data["inn"], None)
            else:
                # Поиск по названию
                egrul_data = dadata_service.find_company_by_name(query)
                if egrul_data:
                    return ("found_one", egrul_data["inn"], None)

            return ("not_found", None, None)

        except Exception as e:
            logger.error(f"Ошибка при fallback поиске через DaData: {e}")
            return ("error", None, None)


# Глобальный экземпляр сервиса
company_search_service = CompanySearchService()
