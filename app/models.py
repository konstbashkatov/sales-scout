"""
Pydantic модели для API
"""
from pydantic import BaseModel, Field
from typing import Optional


class CompanyResearchRequest(BaseModel):
    """
    Запрос на исследование компании

    Используется для прямого вызова API из Битрикс24
    """
    company_name: Optional[str] = Field(None, description="Название компании")
    inn: Optional[str] = Field(None, description="ИНН компании (10 или 12 цифр)")
    user_id: str = Field(..., description="ID пользователя Битрикс24 для отправки результата")

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Яндекс",
                "inn": "7707083893",
                "user_id": "10"
            }
        }


class CompanyResearchResponse(BaseModel):
    """Ответ на запрос исследования компании"""
    status: str = Field(..., description="Статус: success, processing, error")
    message: str = Field(..., description="Сообщение о статусе")
    task_id: Optional[str] = Field(None, description="ID задачи (если асинхронная обработка)")
