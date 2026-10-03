from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models import EntreeType, Unit, MealStatus


class RecipeCreate(BaseModel):
    name: str
    entree_type: EntreeType
    instructions: str
    prep_time_minutes: int
    cook_time_minutes: int
    servings: int = 4
    ingredients: List[dict] = []
    description: Optional[str] = None
    source_url: Optional[str] = None
    tags: Optional[List[str]] = None


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    entree_type: Optional[EntreeType] = None
    instructions: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    servings: Optional[int] = None
    ingredients: Optional[List[dict]] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    tags: Optional[List[str]] = None


class PantryItemCreate(BaseModel):
    name: str
    quantity: float
    unit: Unit
    minimum_threshold: float = 0


class PantryItemUpdate(BaseModel):
    quantity: Optional[float] = None
    unit: Optional[Unit] = None
    minimum_threshold: Optional[float] = None


class MealPlanGenerate(BaseModel):
    start_date: datetime
    days: int = 7
    allowed_entrees: Optional[List[EntreeType]] = None


class MealPlanReplace(BaseModel):
    new_recipe_id: Optional[int] = None
    reason: Optional[str] = None


class ShoppingListGenerate(BaseModel):
    meal_plan_ids: List[int]


class NotionHarvest(BaseModel):
    days_back: int = 7