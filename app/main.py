"""
Sales Scout - FastAPI приложение
Автоматическое создание досье компаний для менеджеров по продажам
"""
import logging
import json
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.webhooks.bitrix_handler import handle_bitrix_message, handle_direct_research_request
from app.models import CompanyResearchRequest, CompanyResearchResponse
from app.config import settings

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sales_scout.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="Sales Scout",
    description="Автоматическое создание досье компаний для менеджеров по продажам",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения"""
    logger.info("=" * 50)
    logger.info("Sales Scout запущен!")
    logger.info(f"Модель LLM: {settings.DEFAULT_MODEL}")
    logger.info(f"Продукт: {settings.OUR_PRODUCT_DESCRIPTION}")
    logger.info("=" * 50)


@app.get("/")
async def root():
    """Главная страница API"""
    return {
        "service": "Sales Scout",
        "version": "1.0.0",
        "status": "running",
        "description": "Автоматическое создание досье компаний для продаж"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "Sales Scout"
    }


@app.post("/webhook/bitrix")
async def bitrix_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint для получения сообщений от Битрикс24

    Args:
        request: HTTP запрос с данными от Битрикс24
        background_tasks: Фоновые задачи FastAPI

    Returns:
        Ответ для Битрикс24
    """
    try:
        # Битрикс24 может отправлять данные как form-data или JSON
        content_type = request.headers.get("content-type", "")

        logger.info(f"Получен webhook от Битрикс24, Content-Type: {content_type}")

        # Получаем сырое тело запроса для отладки
        body = await request.body()
        logger.debug(f"Raw body: {body[:500]}")  # Первые 500 байт

        # Пытаемся распарсить как form-data
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form_data = await request.form()

            # Битрикс24 отправляет данные в формате data[PARAMS][KEY]
            # Преобразуем в нормальную структуру
            data = {
                "event": form_data.get("event", ""),
                "data": {
                    "MESSAGE": {
                        "text": form_data.get("data[PARAMS][MESSAGE]", ""),
                        "chat_id": form_data.get("data[PARAMS][DIALOG_ID]", ""),
                        "author_id": form_data.get("data[PARAMS][AUTHOR_ID]", ""),
                        "system": form_data.get("data[PARAMS][SYSTEM]", "N"),
                    }
                },
                "auth": {
                    "domain": form_data.get("auth[domain]", ""),
                    "application_token": form_data.get("auth[application_token]", ""),
                    "client_endpoint": form_data.get("auth[client_endpoint]", ""),
                }
            }

            logger.info(f"Распарсенные данные от Битрикс24: event={data.get('event')}, message={data['data']['MESSAGE']['text']}, dialog_id={data['data']['MESSAGE']['chat_id']}")
        else:
            # Пытаемся как JSON
            try:
                data = await request.json()
            except:
                # Если не JSON, пытаемся как query params
                data = dict(request.query_params)
                logger.info(f"Данные из query params: {data}")

        logger.info(f"Получен webhook от Битрикс24: event={data.get('event')}")

        # Обрабатываем сообщение в фоне, чтобы быстро ответить Битрикс24
        background_tasks.add_task(handle_bitrix_message, data)

        # Быстро возвращаем OK для Битрикс24
        return JSONResponse({"status": "ok"}, status_code=200)

    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}", exc_info=True)
        # Все равно возвращаем OK чтобы Битрикс24 не пытался повторно отправить
        return JSONResponse({"status": "ok"}, status_code=200)


@app.get("/webhook/research")
async def webhook_research_company(
    companyName: str = None,
    inn: str = None,
    userId: str = None,
    dealTitle: str = None,
    companyWebsite: str = None,
    background_tasks: BackgroundTasks = None
):
    """
    Webhook endpoint для исследования компании (GET запрос с параметрами в URL)

    Пример использования:
    http://aistudy.dev.o2it.ru:8100/webhook/research?companyName=Яндекс&userId=10
    http://aistudy.dev.o2it.ru:8100/webhook/research?companyName={{=Document:TITLE}}&dealTitle={{=Document:DEAL_TITLE}}&inn={{=Document:UF_CRM_INN}}&userId={{=Document:ASSIGNED_BY_ID}}

    Args:
        companyName: Название компании (может быть None)
        inn: ИНН компании (может быть None)
        userId: ID пользователя Битрикс24 (обязательный)
        dealTitle: Название сделки (может быть None)
        companyWebsite: Сайт компании (может быть None)

    Returns:
        Статус обработки
    """
    try:
        logger.info(f"Webhook research: companyName={companyName}, inn={inn}, userId={userId}, dealTitle={dealTitle}, website={companyWebsite}")

        # Проверка что указан userId
        if not userId:
            return JSONResponse({
                "status": "error",
                "message": "Укажите userId"
            }, status_code=400)

        # Определяем что использовать для поиска
        search_query = companyName or dealTitle or inn

        if not search_query:
            return JSONResponse({
                "status": "error",
                "message": "Укажите хотя бы один параметр: companyName, dealTitle или inn"
            }, status_code=400)

        # Запускаем обработку в фоне
        background_tasks.add_task(
            handle_direct_research_request,
            company_name=search_query if not inn else companyName,
            inn=inn,
            user_id=userId
        )

        return JSONResponse({
            "status": "ok",
            "message": f"Исследование компании '{search_query}' запущено"
        })

    except Exception as e:
        logger.error(f"Ошибка webhook research: {e}", exc_info=True)
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@app.post("/api/research", response_model=CompanyResearchResponse)
async def api_research_company(request: CompanyResearchRequest, background_tasks: BackgroundTasks):
    """
    API endpoint для прямого запроса исследования компании

    Используется для вызова из автоматизаций, бизнес-процессов Битрикс24

    Пример запроса:
    POST /api/research
    {
        "company_name": "Яндекс",
        "inn": "7707083893",
        "user_id": "10"
    }

    Args:
        request: Данные запроса (company_name, inn, user_id)
        background_tasks: Фоновые задачи

    Returns:
        Статус обработки запроса
    """
    try:
        logger.info(f"API research request: company_name={request.company_name}, inn={request.inn}, user_id={request.user_id}")

        # Проверка что указано хотя бы название или ИНН
        if not request.company_name and not request.inn:
            return CompanyResearchResponse(
                status="error",
                message="Укажите название компании (company_name) или ИНН (inn)"
            )

        # Обрабатываем запрос в фоне
        background_tasks.add_task(
            handle_direct_research_request,
            company_name=request.company_name,
            inn=request.inn,
            user_id=request.user_id
        )

        query_desc = request.company_name or request.inn

        return CompanyResearchResponse(
            status="processing",
            message=f"Исследование компании '{query_desc}' запущено. Результат будет отправлен пользователю {request.user_id}"
        )

    except Exception as e:
        logger.error(f"Ошибка API research: {e}", exc_info=True)
        return CompanyResearchResponse(
            status="error",
            message=f"Ошибка обработки запроса: {str(e)}"
        )


@app.get("/stats")
async def get_stats():
    """Статистика работы бота"""
    try:
        import os
        import json

        # Читаем feedback_log.jsonl если существует
        if not os.path.exists("feedback_log.jsonl"):
            return {
                "total_feedbacks": 0,
                "positive": 0,
                "negative": 0,
                "feedback_requests": 0
            }

        feedbacks = {"positive": 0, "negative": 0, "feedback": 0}

        with open("feedback_log.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    feedback_type = entry.get("feedback", "")
                    if feedback_type in feedbacks:
                        feedbacks[feedback_type] += 1
                except:
                    continue

        return {
            "total_feedbacks": sum(feedbacks.values()),
            "positive": feedbacks["positive"],
            "negative": feedbacks["negative"],
            "feedback_requests": feedbacks["feedback"]
        }

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
