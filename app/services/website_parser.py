"""
Простой парсер для извлечения контактов с сайтов компаний
"""
import requests
import re
import logging
from typing import Dict, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebsiteParser:
    """Парсер для извлечения контактов с сайтов"""

    def parse_contacts(self, url: str) -> Dict[str, List[str]]:
        """
        Извлечение контактов с сайта компании

        Args:
            url: URL сайта компании

        Returns:
            Словарь с найденными контактами (телефоны, email)
        """
        if not url:
            return {"phones": [], "emails": []}

        try:
            logger.info(f"Парсинг контактов с сайта: {url}")

            # Добавляем https:// если не указан протокол
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()

            # Парсим HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()

            # Также ищем в HTML (для ссылок mailto: и tel:)
            html = response.text

            # Извлекаем телефоны
            phones = self._extract_phones(text, html)

            # Извлекаем email
            emails = self._extract_emails(text, html)

            logger.info(f"Найдено: {len(phones)} телефонов, {len(emails)} email")

            return {
                "phones": phones[:5],  # Максимум 5 телефонов
                "emails": emails[:5],  # Максимум 5 email
            }

        except requests.exceptions.RequestException as e:
            logger.warning(f"Ошибка при парсинге сайта {url}: {e}")
            return {"phones": [], "emails": []}
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге сайта: {e}")
            return {"phones": [], "emails": []}

    def _extract_phones(self, text: str, html: str) -> List[str]:
        """Извлечение телефонных номеров"""
        phones = set()

        # Паттерны для российских номеров
        patterns = [
            # +7 (999) 123-45-67
            r'\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
            # 8 (999) 123-45-67
            r'8[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
            # Из ссылок tel:
            r'tel:\+?[\d\s\-\(\)]+',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            matches_html = re.findall(pattern, html, re.IGNORECASE)
            phones.update(matches)
            phones.update(matches_html)

        # Нормализуем номера
        normalized = []
        for phone in phones:
            # Убираем tel: prefix
            phone = phone.replace('tel:', '').replace('Tel:', '').strip()
            # Убираем лишние символы, оставляем только цифры и + в начале
            phone = re.sub(r'[^\d\+]', '', phone)
            if phone and len(phone) >= 10:
                normalized.append(phone)

        return list(set(normalized))

    def _extract_emails(self, text: str, html: str) -> List[str]:
        """Извлечение email адресов"""
        emails = set()

        # Паттерн для email
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

        # Ищем в тексте и HTML
        matches_text = re.findall(pattern, text, re.IGNORECASE)
        matches_html = re.findall(pattern, html, re.IGNORECASE)

        emails.update(matches_text)
        emails.update(matches_html)

        # Фильтруем очевидно невалидные email
        filtered = []
        exclude_domains = ['example.com', 'test.com', 'domain.com', 'yourcompany.com']
        exclude_prefixes = ['image', 'photo', 'picture', 'icon']

        for email in emails:
            email = email.lower().strip()
            # Проверяем что это не картинка или тестовый email
            if not any(excl in email for excl in exclude_domains + exclude_prefixes):
                if len(email) < 50:  # Разумная длина
                    filtered.append(email)

        return list(set(filtered))


# Глобальный экземпляр парсера
website_parser = WebsiteParser()
