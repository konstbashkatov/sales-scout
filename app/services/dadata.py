"""
DaData API сервис для получения данных о компаниях из ЕГРЮЛ
"""
import requests
import logging
from typing import Optional, Dict

from app.config import settings

logger = logging.getLogger(__name__)


class DaDataService:
    """Сервис для работы с DaData API"""

    def __init__(self):
        self.api_key = settings.DADATA_API_KEY
        self.base_url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs"

    def find_company_by_inn(self, inn: str) -> Optional[Dict]:
        """
        Поиск компании по ИНН в базе ЕГРЮЛ

        Args:
            inn: ИНН компании (10 или 12 цифр)

        Returns:
            Словарь с данными компании или None если не найдена
        """
        url = f"{self.base_url}/findById/party"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                url,
                json={"query": inn},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get("suggestions"):
                company_data = data["suggestions"][0]["data"]
                return self._format_company_data(company_data)
            else:
                logger.warning(f"Company with INN {inn} not found in DaData")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching company data from DaData: {e}")
            raise

    def find_company_by_name(self, company_name: str) -> Optional[Dict]:
        """
        Поиск компании по названию в базе ЕГРЮЛ

        Args:
            company_name: Название компании

        Returns:
            Словарь с данными компании или None если не найдена
        """
        url = f"{self.base_url}/suggest/party"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            logger.info(f"Поиск компании по названию: {company_name}")

            response = requests.post(
                url,
                json={"query": company_name, "count": 5},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get("suggestions"):
                # Берем первый результат (наиболее релевантный)
                company_data = data["suggestions"][0]["data"]
                logger.info(f"Найдена компания: {data['suggestions'][0]['value']}")
                return self._format_company_data(company_data)
            else:
                logger.warning(f"Company with name '{company_name}' not found in DaData")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching company by name in DaData: {e}")
            raise

    def _format_company_data(self, raw_data: Dict) -> Dict:
        """
        Форматирование сырых данных от DaData в удобный формат

        Args:
            raw_data: Сырые данные от DaData API

        Returns:
            Отформатированный словарь с данными компании
        """
        # Безопасное извлечение вложенных данных (защита от None)
        name_data = raw_data.get("name") or {}
        state_data = raw_data.get("state") or {}
        management_data = raw_data.get("management") or {}
        address_data = raw_data.get("address") or {}
        address_nested = address_data.get("data") or {}
        capital_data = raw_data.get("capital") or {}

        return {
            "full_name": name_data.get("full_with_opf", ""),
            "short_name": name_data.get("short_with_opf", ""),
            "inn": raw_data.get("inn", ""),
            "kpp": raw_data.get("kpp", ""),
            "ogrn": raw_data.get("ogrn", ""),
            "okved": raw_data.get("okved", ""),
            "status": state_data.get("status", ""),
            "registration_date": state_data.get("registration_date"),
            "director": {
                "name": management_data.get("name", ""),
                "post": management_data.get("post", "Генеральный директор")
            },
            "address": {
                "full": address_data.get("value", ""),
                "region": address_nested.get("region", ""),
                "city": address_nested.get("city", ""),
            },
            "capital": capital_data.get("value"),
            "employee_count": raw_data.get("employee_count"),
        }


# Глобальный экземпляр сервиса
dadata_service = DaDataService()
