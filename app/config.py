from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Notion
    notion_token: Optional[str] = None
    notion_database_id: Optional[str] = None
    notion_pantry_database_id: Optional[str] = None

    # Database
    database_url: str = "sqlite:///./meal_planner.db"

    # Scheduler
    morning_delivery_hour: int = 8
    morning_delivery_minute: int = 0
    weekly_harvest_day: str = "sunday"
    weekly_harvest_hour: int = 10

    # Meal Planning
    default_entrees: list[str] = [
        "beef", "pork", "chicken", "haddock", "salmon",
        "shrimp", "tofu", "eggs", "ground_beef", "ground_turkey"
    ]
    days_to_plan: int = 7

    # Staples (ingredients assumed always available)
    staple_ingredients: list[str] = [
        "salt", "pepper", "olive_oil", "vegetable_oil", "butter",
        "garlic", "onion", "flour", "sugar", "rice", "pasta",
        "soy_sauce", "vinegar"
    ]

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()