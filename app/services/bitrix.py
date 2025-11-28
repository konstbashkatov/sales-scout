"""
Bitrix24 API сервис для отправки сообщений в чат
"""
import requests
import logging
from typing import List, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class BitrixService:
    """Сервис для работы с Bitrix24 API"""

    def __init__(self):
        self.webhook_url = settings.BITRIX24_WEBHOOK_URL
        self.bot_id = settings.BITRIX24_BOT_ID
        self.client_id = settings.BITRIX24_CLIENT_ID

    def _split_message(self, message: str, max_length: int = 4000) -> List[str]:
        """
        Разбивает длинное сообщение на части

        Args:
            message: Исходное сообщение
            max_length: Максимальная длина одной части

        Returns:
            Список частей сообщения
        """
        if len(message) <= max_length:
            return [message]

        parts = []
        current_part = ""

        for line in message.split('\n'):
            if len(current_part) + len(line) + 1 > max_length:
                if current_part:
                    parts.append(current_part.strip())
                current_part = line + '\n'
            else:
                current_part += line + '\n'

        if current_part:
            parts.append(current_part.strip())

        return parts

    def send_message(self, dialog_id: str, message: str, keyboard: Optional[List[Dict]] = None) -> Dict:
        """
        Отправка сообщения в чат Битрикс24

        Args:
            dialog_id: ID диалога (chat ID или user ID)
            message: Текст сообщения
            keyboard: Клавиатура с кнопками (опционально)

        Returns:
            Ответ от API Битрикс24
        """
        # Формат для личного чата - просто user ID
        # Формат для группового чата - chat{ID}
        formatted_dialog_id = dialog_id

        # Используем GET для простых сообщений, POST для сообщений с кнопками
        url = f"{self.webhook_url}/imbot.message.add.json"

        params = {
            "BOT_ID": self.bot_id,
            "CLIENT_ID": self.client_id,
            "DIALOG_ID": formatted_dialog_id,
            "MESSAGE": message
        }

        # Разбиваем длинное сообщение на части
        message_parts = self._split_message(message, max_length=4000)

        try:
            logger.info(f"Отправка сообщения в диалог {formatted_dialog_id} от бота {self.bot_id}")
            logger.info(f"Сообщение разбито на {len(message_parts)} частей")

            results = []

            # Отправляем все части
            for i, part in enumerate(message_parts):
                params_part = params.copy()
                params_part["MESSAGE"] = part

                # Кнопки прикрепляем только к последней части
                is_last_part = (i == len(message_parts) - 1)

                # Используем GET только для очень коротких сообщений (<200 символов)
                # Для досье и длинных сообщений - всегда POST
                use_post = len(part) > 200 or (keyboard and is_last_part)

                if keyboard and is_last_part:
                    import json as json_lib
                    params_part["KEYBOARD"] = json_lib.dumps(keyboard, ensure_ascii=False)

                if use_post:
                    logger.debug(f"Отправка части {i+1}/{len(message_parts)} через POST")
                    response = requests.post(url, data=params_part, timeout=30)
                else:
                    logger.debug(f"Отправка части {i+1}/{len(message_parts)} через GET")
                    response = requests.get(url, params=params_part, timeout=30)

                response.raise_for_status()

                result = response.json()

                if result.get("error"):
                    logger.error(f"Ошибка API Битрикс24: {result}")
                    raise Exception(f"Bitrix24 API error: {result.get('error_description', result.get('error'))}")

                results.append(result)
                logger.info(f"Часть {i+1}/{len(message_parts)} отправлена: message_id={result.get('result')}")

                # Небольшая задержка между частями
                if i < len(message_parts) - 1:
                    import time
                    time.sleep(0.5)

            logger.info(f"Все части сообщения отправлены успешно")

            return results[-1]  # Возвращаем результат последней части

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка отправки сообщения в Битрикс24: {e}")
            logger.error(f"URL: {url}")
            raise

    def create_feedback_keyboard(self, company_id: str) -> List[List[Dict]]:
        """
        Создание клавиатуры с кнопками оценки для Битрикс24

        Args:
            company_id: ИНН или название компании (для передачи в callback)

        Returns:
            Клавиатура в формате Битрикс24
        """
        # Формат клавиатуры Битрикс24: массив рядов, каждый ряд - массив кнопок
        return [
            [
                {
                    "TEXT": "👍 Полезно",
                    "BOT_ID": self.bot_id,
                    "COMMAND": "positive",
                    "COMMAND_PARAMS": company_id,
                    "DISPLAY": "LINE",
                    "BG_COLOR": "#29c75f",
                    "TEXT_COLOR": "#fff"
                }
            ],
            [
                {
                    "TEXT": "👎 Не полезно",
                    "BOT_ID": self.bot_id,
                    "COMMAND": "negative",
                    "COMMAND_PARAMS": company_id,
                    "DISPLAY": "LINE",
                    "BG_COLOR": "#ff4d4d",
                    "TEXT_COLOR": "#fff"
                }
            ],
            [
                {
                    "TEXT": "💬 Оставить отзыв",
                    "BOT_ID": self.bot_id,
                    "COMMAND": "feedback",
                    "COMMAND_PARAMS": company_id,
                    "DISPLAY": "LINE",
                    "BG_COLOR": "#2196F3",
                    "TEXT_COLOR": "#fff"
                }
            ]
        ]

    def send_typing_notification(self, dialog_id: str):
        """
        Отправка уведомления "печатает..."

        Args:
            dialog_id: ID диалога
        """
        # В Битрикс24 это происходит автоматически при длительной обработке
        pass

    def add_deal_comment(self, deal_id: str, comment: str) -> Dict:
        """
        Добавление комментария к сделке в CRM Битрикс24

        Args:
            deal_id: ID сделки
            comment: Текст комментария

        Returns:
            Ответ от API Битрикс24
        """
        url = f"{self.webhook_url}/crm.timeline.comment.add.json"

        params = {
            "fields": {
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "deal",
                "COMMENT": comment
            }
        }

        try:
            logger.info(f"Добавление комментария к сделке {deal_id}")

            response = requests.post(url, json=params, timeout=30)
            response.raise_for_status()

            result = response.json()

            if result.get("error"):
                logger.error(f"Ошибка API Битрикс24 при добавлении комментария: {result}")
                raise Exception(f"Bitrix24 API error: {result.get('error_description', result.get('error'))}")

            logger.info(f"Комментарий к сделке {deal_id} успешно добавлен: comment_id={result.get('result')}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка добавления комментария к сделке {deal_id}: {e}")
            raise


# Глобальный экземпляр сервиса
bitrix_service = BitrixService()
