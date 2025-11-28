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
        return {
            "full_name": raw_data.get("name", {}).get("full_with_opf", ""),
            "short_name": raw_data.get("name", {}).get("short_with_opf", ""),
            "inn": raw_data.get("inn", ""),
            "kpp": raw_data.get("kpp", ""),
            "ogrn": raw_data.get("ogrn", ""),
            "okved": raw_data.get("okved", ""),
            "status": raw_data.get("state", {}).get("status", ""),
            "registration_date": raw_data.get("state", {}).get("registration_date"),
            "director": {
                "name": raw_data.get("management", {}).get("name", ""),
                "post": raw_data.get("management", {}).get("post", "Генеральный директор")
            },
            "address": {
                "full": raw_data.get("address", {}).get("value", ""),
                "region": raw_data.get("address", {}).get("data", {}).get("region", ""),
                "city": raw_data.get("address", {}).get("data", {}).get("city", ""),
            },
            "capital": raw_data.get("capital", {}).get("value"),
            "employee_count": raw_data.get("employee_count"),
        }


# Глобальный экземпляр сервиса
dadata_service = DaDataService()
