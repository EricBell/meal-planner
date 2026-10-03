from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr


class EntreeType(str, Enum):
    BEEF = "beef"
    PORK = "pork"
    CHICKEN = "chicken"
    HADDOCK = "haddock"
    SALMON = "salmon"
    SHRIMP = "shrimp"
    TOFU = "tofu"
    EGGS = "eggs"
    GROUND_BEEF = "ground_beef"
    GROUND_TURKEY = "ground_turkey"


class Unit(str, Enum):
    GRAMS = "g"
    KILOGRAMS = "kg"
    OUNCES = "oz"
    POUNDS = "lb"
    ML = "ml"
    LITERS = "l"
    CUPS = "cup"
    TBSP = "tbsp"
    TSP = "tsp"
    PIECES = "pcs"
    CLoves = "cloves"
    CANS = "cans"
    PINCH = "pinch"
    TO_TASTE = "to_taste"


class MealStatus(str, Enum):
    PLANNED = "planned"
    CONFIRMED = "confirmed"
    COOKED = "cooked"
    SKIPPED = "skipped"
    REPLACED = "replaced"


class Ingredient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    is_staple: bool = Field(default=False)
    default_unit: Unit = Field(default=Unit.GRAMS)
    category: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecipeIngredient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    recipe_id: int = Field(foreign_key="recipe.id", ondelete="CASCADE")
    ingredient_id: int = Field(foreign_key="ingredient.id", ondelete="CASCADE")
    quantity: float
    unit: Unit
    notes: Optional[str] = None
    is_optional: bool = Field(default=False)

    # Relationships
    ingredient: "Ingredient" = Relationship()
    recipe: "Recipe" = Relationship(back_populates="ingredients")


class Recipe(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    entree_type: EntreeType = Field(index=True)
    description: Optional[str] = None
    instructions: str
    prep_time_minutes: int
    cook_time_minutes: int
    servings: int = Field(default=4)
    source_url: Optional[str] = None
    source_notion_page_id: Optional[str] = None
    tags: Optional[str] = None  # JSON array as string
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    ingredients: list[RecipeIngredient] = Relationship(back_populates="recipe")


class PantryItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id", ondelete="CASCADE", unique=True)
    quantity_on_hand: float = Field(default=0)
    unit: Unit
    minimum_threshold: float = Field(default=0)  # Alert when below this
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notion_page_id: Optional[str] = None

    # Relationships
    ingredient: "Ingredient" = Relationship()


class MealPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime = Field(index=True)
    recipe_id: int = Field(foreign_key="recipe.id", ondelete="CASCADE")
    status: MealStatus = Field(default=MealStatus.PLANNED, index=True)
    notes: Optional[str] = None
    replacement_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    recipe: "Recipe" = Relationship()


class ShoppingList(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id", ondelete="CASCADE")
    quantity_needed: float
    unit: Unit
    meal_plan_ids: str  # JSON array of meal plan IDs
    is_purchased: bool = Field(default=False)
    purchased_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    ingredient: "Ingredient" = Relationship()


class NotionSyncLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sync_type: str  # "harvest", "push", "pull"
    entity_type: str  # "recipe", "meal_plan", "pantry"
    entity_id: int
    notion_page_id: str
    status: str  # "success", "failed", "skipped"
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))