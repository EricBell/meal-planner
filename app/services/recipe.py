from typing import Optional
from sqlmodel import Session, select
from app.models import (
    Recipe, RecipeIngredient, MealPlan, EntreeType,
    Ingredient, MealStatus, Unit
)
from app.database import get_session_sync
from app.services.pantry import PantryService
from collections import defaultdict
import random
import json
from datetime import datetime, timedelta, timezone


class RecipeService:
    """Manages recipes and meal planning logic."""

    def __init__(self, session: Session):
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    # --- Recipe CRUD ---

    def create_recipe(
        self,
        name: str,
        entree_type: EntreeType,
        instructions: str,
        prep_time_minutes: int,
        cook_time_minutes: int,
        servings: int = 4,
        ingredients: list[dict] = None,
        description: Optional[str] = None,
        source_url: Optional[str] = None,
        source_notion_page_id: Optional[str] = None,
        tags: list[str] = None
    ) -> Recipe:
        """Create a new recipe with ingredients."""
        recipe = Recipe(
            name=name,
            entree_type=entree_type,
            description=description,
            instructions=instructions,
            prep_time_minutes=prep_time_minutes,
            cook_time_minutes=cook_time_minutes,
            servings=servings,
            source_url=source_url,
            source_notion_page_id=source_notion_page_id,
            tags=json.dumps(tags) if tags else None
        )
        self.session.add(recipe)
        self.session.flush()

        if ingredients:
            for ing_data in ingredients:
                ingredient = self._get_or_create_ingredient(ing_data["name"])
                recipe_ing = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    quantity=ing_data["quantity"],
                    unit=ing_data["unit"],
                    notes=ing_data.get("notes"),
                    is_optional=ing_data.get("is_optional", False)
                )
                self.session.add(recipe_ing)

        self.session.flush()
        return recipe

    def _get_or_create_ingredient(self, name: str) -> Ingredient:
        stmt = select(Ingredient).where(Ingredient.name == name.lower().strip())
        ingredient = self.session.exec(stmt).first()
        if not ingredient:
            ingredient = Ingredient(name=name.lower().strip())
            self.session.add(ingredient)
            self.session.flush()
        return ingredient

    def get_recipe(self, recipe_id: int) -> Optional[Recipe]:
        stmt = select(Recipe).where(Recipe.id == recipe_id)
        return self.session.exec(stmt).first()

    def get_recipes_by_entree(self, entree_type: EntreeType) -> list[Recipe]:
        stmt = select(Recipe).where(Recipe.entree_type == entree_type).order_by(Recipe.name)
        return list(self.session.exec(stmt).all())

    def search_recipes(self, query: str) -> list[Recipe]:
        stmt = select(Recipe).where(Recipe.name.contains(query)).order_by(Recipe.name)
        return list(self.session.exec(stmt).all())

    def list_all_recipes(self) -> list[Recipe]:
        stmt = select(Recipe).order_by(Recipe.entree_type, Recipe.name)
        return list(self.session.exec(stmt).all())

    def delete_recipe(self, recipe_id: int) -> bool:
        recipe = self.get_recipe(recipe_id)
        if recipe:
            self.session.delete(recipe)
            self.session.flush()
            return True
        return False

    # --- Meal Planning ---

    def generate_meal_plan(
        self,
        start_date: datetime,
        days: int = 7,
        allowed_entrees: list[EntreeType] = None,
        avoid_recent_days: int = 14
    ) -> list[MealPlan]:
        """Generate a meal plan for the given date range."""
        if allowed_entrees is None:
            allowed_entrees = list(EntreeType)

        # Get recently used recipes to avoid repetition
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=avoid_recent_days)
        stmt = select(MealPlan.recipe_id).where(
            MealPlan.date >= recent_cutoff,
            MealPlan.status.in_([MealStatus.COOKED, MealStatus.CONFIRMED])
        )
        recent_recipe_ids = set(self.session.exec(stmt).all())

        meal_plans = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)

        for day_offset in range(days):
            date = current_date + timedelta(days=day_offset)

            # Check if already planned
            stmt = select(MealPlan).where(MealPlan.date == date)
            existing = self.session.exec(stmt).first()
            if existing:
                meal_plans.append(existing)
                continue

            # Pick entree type (rotate through allowed)
            entree = allowed_entrees[day_offset % len(allowed_entrees)]

            # Get recipes for this entree, excluding recent
            recipes = self.get_recipes_by_entree(entree)
            available = [r for r in recipes if r.id not in recent_recipe_ids]

            if not available:
                # Fallback: allow recent if no other options
                available = recipes

            if not available:
                continue  # No recipes for this entree

            recipe = random.choice(available)
            recent_recipe_ids.add(recipe.id)

            meal_plan = MealPlan(
                date=date,
                recipe_id=recipe.id,
                status=MealStatus.PLANNED
            )
            self.session.add(meal_plan)
            meal_plans.append(meal_plan)

        self.session.flush()
        return meal_plans

    def get_meal_plan(self, date: datetime) -> Optional[MealPlan]:
        stmt = select(MealPlan).where(MealPlan.date == date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc))
        return self.session.exec(stmt).first()

    def get_meal_plans_range(self, start: datetime, end: datetime) -> list[MealPlan]:
        stmt = select(MealPlan).where(
            MealPlan.date >= start.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc),
            MealPlan.date <= end.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        ).order_by(MealPlan.date)
        return list(self.session.exec(stmt).all())

    def confirm_meal_plan(self, meal_plan_id: int) -> Optional[MealPlan]:
        stmt = select(MealPlan).where(MealPlan.id == meal_plan_id)
        mp = self.session.exec(stmt).first()
        if mp:
            mp.status = MealStatus.CONFIRMED
            mp.updated_at = datetime.now(timezone.utc)
            self.session.flush()
        return mp

    def replace_meal_plan(
        self,
        meal_plan_id: int,
        reason: str = None,
        new_recipe_id: int = None
    ) -> Optional[MealPlan]:
        """Replace a meal plan with a new recipe."""
        stmt = select(MealPlan).where(MealPlan.id == meal_plan_id)
        mp = self.session.exec(stmt).first()
        if not mp:
            return None

        old_recipe_id = mp.recipe_id

        if new_recipe_id:
            new_recipe = self.get_recipe(new_recipe_id)
            if not new_recipe:
                return None
            mp.recipe_id = new_recipe_id
        else:
            # Auto-pick alternative with same entree
            old_recipe = self.get_recipe(old_recipe_id)
            if not old_recipe:
                return None

            recipes = self.get_recipes_by_entree(old_recipe.entree_type)
            alternatives = [r for r in recipes if r.id != old_recipe_id]
            if not alternatives:
                return None

            mp.recipe_id = random.choice(alternatives).id

        mp.status = MealStatus.REPLACED
        mp.replacement_reason = reason
        mp.updated_at = datetime.now(timezone.utc)
        self.session.flush()
        return mp

    def mark_cooked(self, meal_plan_id: int) -> Optional[MealPlan]:
        stmt = select(MealPlan).where(MealPlan.id == meal_plan_id)
        mp = self.session.exec(stmt).first()
        if mp:
            mp.status = MealStatus.COOKED
            mp.updated_at = datetime.now(timezone.utc)
            # Consume ingredients from pantry
            pantry = PantryService(self.session)
            recipe = self.get_recipe(mp.recipe_id)
            for ri in recipe.ingredients:
                if not ri.is_optional:
                    pantry.consume_from_pantry(ri.ingredient.name, ri.quantity, ri.unit)
            self.session.flush()
        return mp

    def skip_meal_plan(self, meal_plan_id: int) -> Optional[MealPlan]:
        stmt = select(MealPlan).where(MealPlan.id == meal_plan_id)
        mp = self.session.exec(stmt).first()
        if mp:
            mp.status = MealStatus.SKIPPED
            mp.updated_at = datetime.now(timezone.utc)
            self.session.flush()
        return mp

    # --- Recipe Details for Display ---

    def get_recipe_with_ingredients(self, recipe_id: int) -> Optional[dict]:
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return None

        stmt = select(RecipeIngredient, Ingredient).join(Ingredient).where(
            RecipeIngredient.recipe_id == recipe_id
        )
        results = self.session.exec(stmt).all()

        ingredients = []
        for ri, ing in results:
            ingredients.append({
                "name": ing.name,
                "quantity": ri.quantity,
                "unit": ri.unit.value,
                "notes": ri.notes,
                "is_optional": ri.is_optional,
                "is_staple": ing.is_staple
            })

        return {
            "id": recipe.id,
            "name": recipe.name,
            "entree_type": recipe.entree_type.value,
            "description": recipe.description,
            "instructions": recipe.instructions,
            "prep_time_minutes": recipe.prep_time_minutes,
            "cook_time_minutes": recipe.cook_time_minutes,
            "servings": recipe.servings,
            "source_url": recipe.source_url,
            "tags": json.loads(recipe.tags) if recipe.tags else [],
            "ingredients": ingredients
        }