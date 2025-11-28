"""
Обработчик webhook от Битрикс24
"""
import re
import logging
from typing import Dict

from app.services.bitrix import bitrix_service
from app.services.sales_analyzer import sales_analyzer

logger = logging.getLogger(__name__)


def extract_inn(text: str) -> str:
    """
    Извлечение ИНН из текста сообщения

    Args:
        text: Текст сообщения от пользователя

    Returns:
        ИНН или None если не найден
    """
    # ИНН может быть 10 или 12 цифр
    match = re.search(r'\b\d{10,12}\b', text)
    return match.group(0) if match else None


def is_company_query(text: str) -> bool:
    """
    Проверка что сообщение содержит запрос о компании

    Args:
        text: Текст сообщения

    Returns:
        True если это запрос о компании
    """
    # Игнорируем команды от кнопок
    if text.strip().lower() in ["positive", "negative", "feedback"]:
        return False

    # Если есть ИНН - это точно запрос
    if extract_inn(text):
        return True

    # Если сообщение длиннее 2 символов - считаем что это название компании
    if len(text.strip()) >= 2:
        return True

    return False


async def handle_bitrix_message(webhook_data: Dict):
    """
    Обработка входящего сообщения от Битрикс24

    Args:
        webhook_data: Данные webhook от Битрикс24
    """
    try:
        event = webhook_data.get("event")

        # Обрабатываем только сообщения
        if event != "ONIMBOTMESSAGEADD":
            logger.debug(f"Игнорируем событие: {event}")
            return

        message_data = webhook_data.get("data", {}).get("MESSAGE", {})

        # Игнорируем системные сообщения
        if message_data.get("system") == "Y":
            logger.debug("Игнорируем системное сообщение")
            return

        text = message_data.get("text", "")
        dialog_id = message_data.get("chat_id")

        # Извлекаем auth токен из webhook данных (для отправки ответов)
        auth_data = webhook_data.get("auth", {})

        if not dialog_id:
            logger.warning("Отсутствует dialog_id в сообщении")
            return

        logger.info(f"Получено сообщение из диалога {dialog_id}: {text}")

        # Проверяем, это команда от кнопки или обычное сообщение
        if text in ["positive", "negative", "feedback"]:
            await handle_feedback(dialog_id, text, webhook_data)
            return

        # СРАЗУ ОТПРАВЛЯЕМ БЫСТРУЮ РЕАКЦИЮ (только для новых запросов)
        bitrix_service.send_message(
            dialog_id,
            "✅ Запрос получен! Формирую детальное досье компании.\n\n⏱️ Это займет 1-3 минуты, вернусь с результатами..."
        )

        # Проверяем что это запрос о компании
        if not is_company_query(text):
            bitrix_service.send_message(
                dialog_id,
                "❓ Пожалуйста, отправьте:\n\n"
                "• ИНН компании (10 или 12 цифр), например: 7707083893\n"
                "• или название компании, например: Яндекс\n"
                "• или название компании, например: ООО Рога и Копыта"
            )
            return

        # Определяем тип запроса
        inn = extract_inn(text)

        if inn:
            # Поиск по ИНН
            logger.info(f"Найден ИНН: {inn}")
            company_identifier = inn
        else:
            # Поиск по названию
            company_name_query = text.strip()
            logger.info(f"Поиск по названию: {company_name_query}")
            company_identifier = company_name_query

        # Создаем досье компании
        try:
            if inn:
                dossier = await sales_analyzer.create_company_dossier(inn=inn)
                feedback_id = inn
            else:
                dossier = await sales_analyzer.create_company_dossier(company_name=company_name_query)
                # Для кнопок оценки используем название (если ИНН не был найден)
                feedback_id = company_name_query

            # Отправляем досье БЕЗ кнопок (чтобы избежать 400 ошибки)
            bitrix_service.send_message(
                dialog_id,
                dossier,
                keyboard=None  # Пока без кнопок
            )

            logger.info(f"Досье для {company_identifier} успешно отправлено")

            # Отправляем кнопки отдельным сообщением (только если досье успешно)
            if not dossier.startswith("❌") and not dossier.startswith("😔"):
                try:
                    keyboard = bitrix_service.create_feedback_keyboard(feedback_id)
                    bitrix_service.send_message(
                        dialog_id,
                        "Оцените полезность досье:",
                        keyboard=keyboard
                    )
                    logger.info("Кнопки оценки отправлены")
                except Exception as e:
                    logger.warning(f"Не удалось отправить кнопки оценки: {e}")
                    # Не критично, продолжаем работу

        except Exception as e:
            logger.error(f"Ошибка при создании досье: {e}", exc_info=True)

            # Отправляем понятное сообщение пользователю
            try:
                bitrix_service.send_message(
                    dialog_id,
                    f"😔 К сожалению, не удалось собрать информацию о компании '{company_identifier}'.\n\n"
                    "Возможные причины:\n"
                    "• Компания не зарегистрирована в России\n"
                    "• Неправильное название или ИНН\n"
                    "• Временные проблемы с источниками данных\n\n"
                    "Попробуйте:\n"
                    "• Уточнить название компании\n"
                    "• Использовать ИНН (10 или 12 цифр)\n"
                    "• Попробовать через несколько минут"
                )
            except:
                logger.error("Не удалось отправить сообщение об ошибке")

    except Exception as e:
        logger.error(f"Критическая ошибка при обработке сообщения: {e}", exc_info=True)


async def handle_feedback(dialog_id: str, feedback_type: str, webhook_data: Dict):
    """
    Обработка нажатия на кнопку оценки

    Args:
        dialog_id: ID диалога
        feedback_type: Тип оценки (positive/negative/feedback)
        webhook_data: Данные webhook
    """
    try:
        # Извлекаем идентификатор компании из параметров команды
        params = webhook_data.get("data", {}).get("MESSAGE", {}).get("params", {})
        command_params = params.get("COMMAND_PARAMS", "")

        company_id = command_params.replace("company=", "") if command_params else "неизвестна"

        logger.info(f"Получена оценка '{feedback_type}' для компании {company_id}")

        if feedback_type == "positive":
            message = "✅ Спасибо за положительную оценку! Рад, что досье было полезным."

        elif feedback_type == "negative":
            message = "📝 Спасибо за оценку. Мы работаем над улучшением качества информации."

        elif feedback_type == "feedback":
            message = "💬 Пожалуйста, напишите ваш отзыв или предложения в следующем сообщении. Мы обязательно их учтем!"

        else:
            message = "❓ Неизвестная команда"

        bitrix_service.send_message(dialog_id, message)

        # Здесь можно добавить логирование оценок в файл или БД
        _log_feedback(company_id, feedback_type, dialog_id)

    except Exception as e:
        logger.error(f"Ошибка при обработке оценки: {e}", exc_info=True)


async def handle_direct_research_request(company_name: str = None, inn: str = None, user_id: str = None, deal_id: str = None, company_website: str = None):
    """
    Обработка прямого API запроса на исследование компании

    Args:
        company_name: Название компании
        inn: ИНН компании
        user_id: ID пользователя Битрикс24 для отправки результата
        deal_id: ID сделки для добавления комментария с досье
        company_website: Сайт компании (если известен)
    """
    try:
        logger.info(f"Прямой API запрос: company_name={company_name}, inn={inn}, user_id={user_id}, deal_id={deal_id}, website={company_website}")

        if not user_id:
            logger.error("Отсутствует user_id в запросе")
            return

        # Отправляем быструю отбивку пользователю
        bitrix_service.send_message(
            user_id,
            f"✅ Запрос на исследование компании '{company_name or inn}' получен!\n\n"
            "⏱️ Формирование детального досье займет 1-3 минуты.\n\n"
            "Собираю информацию из интернета..."
        )

        # Создаем досье
        try:
            if inn:
                dossier = await sales_analyzer.create_company_dossier(inn=inn, company_website=company_website)
                feedback_id = inn
            else:
                dossier = await sales_analyzer.create_company_dossier(company_name=company_name, company_website=company_website)
                feedback_id = company_name

            # Отправляем досье
            bitrix_service.send_message(
                user_id,
                dossier,
                keyboard=None
            )

            # Добавляем комментарий к сделке если указан deal_id
            if deal_id and not dossier.startswith("❌") and not dossier.startswith("😔"):
                try:
                    bitrix_service.add_deal_comment(deal_id, dossier)
                    logger.info(f"Досье добавлено как комментарий к сделке {deal_id}")
                except Exception as e:
                    logger.warning(f"Не удалось добавить комментарий к сделке {deal_id}: {e}")

            # Отправляем кнопки оценки
            if not dossier.startswith("❌") and not dossier.startswith("😔"):
                try:
                    keyboard = bitrix_service.create_feedback_keyboard(feedback_id)
                    bitrix_service.send_message(
                        user_id,
                        "Оцените полезность досье:",
                        keyboard=keyboard
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить кнопки оценки: {e}")

            logger.info(f"Досье для {company_name or inn} отправлено пользователю {user_id}")

        except Exception as e:
            logger.error(f"Ошибка при создании досье: {e}", exc_info=True)

            # Отправляем понятное сообщение об ошибке
            bitrix_service.send_message(
                user_id,
                f"😔 К сожалению, не удалось собрать информацию о компании '{company_name or inn}'.\n\n"
                "Возможные причины:\n"
                "• Компания не зарегистрирована в России\n"
                "• Неправильное название или ИНН\n"
                "• Временные проблемы с источниками данных\n\n"
                "Попробуйте:\n"
                "• Уточнить название компании\n"
                "• Использовать ИНН (10 или 12 цифр)\n"
                "• Попробовать через несколько минут"
            )

    except Exception as e:
        logger.error(f"Критическая ошибка в прямом API запросе: {e}", exc_info=True)


def _log_feedback(company_id: str, feedback_type: str, dialog_id: str):
    """
    Логирование оценок в файл

    Args:
        company_id: ИНН или название компании
        feedback_type: Тип оценки
        dialog_id: ID диалога
    """
    try:
        from datetime import datetime
        import json

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "company": company_id,
            "feedback": feedback_type,
            "dialog_id": dialog_id
        }

        with open("feedback_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        logger.info(f"Оценка '{feedback_type}' для компании '{company_id}' записана в лог")

    except Exception as e:
        logger.error(f"Ошибка при записи оценки в лог: {e}")
