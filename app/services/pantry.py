from typing import Optional
from sqlmodel import Session, select
from app.models import (
    Ingredient, PantryItem, Recipe, RecipeIngredient,
    ShoppingList, MealPlan, Unit, EntreeType, MealStatus
)
from app.database import get_session_sync
from collections import defaultdict
import json


class PantryService:
    """Manages pantry inventory and shopping list generation."""

    def __init__(self, session: Session):
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    # --- Ingredient CRUD ---

    def get_or_create_ingredient(
        self,
        name: str,
        is_staple: bool = False,
        default_unit: Unit = Unit.GRAMS,
        category: Optional[str] = None
    ) -> Ingredient:
        """Get existing ingredient or create new one."""
        stmt = select(Ingredient).where(Ingredient.name == name.lower().strip())
        ingredient = self.session.exec(stmt).first()
        if not ingredient:
            ingredient = Ingredient(
                name=name.lower().strip(),
                is_staple=is_staple,
                default_unit=default_unit,
                category=category
            )
            self.session.add(ingredient)
            self.session.flush()
        return ingredient

    def get_ingredient(self, name: str) -> Optional[Ingredient]:
        stmt = select(Ingredient).where(Ingredient.name == name.lower().strip())
        return self.session.exec(stmt).first()

    def list_ingredients(self) -> list[Ingredient]:
        stmt = select(Ingredient).order_by(Ingredient.name)
        return list(self.session.exec(stmt).all())

    def list_staples(self) -> list[Ingredient]:
        stmt = select(Ingredient).where(Ingredient.is_staple == True).order_by(Ingredient.name)
        return list(self.session.exec(stmt).all())

    # --- Pantry Item CRUD ---

    def set_pantry_quantity(
        self,
        ingredient_name: str,
        quantity: float,
        unit: Unit,
        minimum_threshold: float = 0
    ) -> PantryItem:
        """Set quantity on hand for an ingredient."""
        ingredient = self.get_or_create_ingredient(ingredient_name)
        stmt = select(PantryItem).where(PantryItem.ingredient_id == ingredient.id)
        pantry_item = self.session.exec(stmt).first()

        if pantry_item:
            pantry_item.quantity_on_hand = quantity
            pantry_item.unit = unit
            pantry_item.minimum_threshold = minimum_threshold
        else:
            pantry_item = PantryItem(
                ingredient_id=ingredient.id,
                quantity_on_hand=quantity,
                unit=unit,
                minimum_threshold=minimum_threshold
            )
            self.session.add(pantry_item)

        self.session.flush()
        return pantry_item

    def add_to_pantry(self, ingredient_name: str, quantity: float, unit: Unit) -> PantryItem:
        """Add quantity to existing pantry item."""
        ingredient = self.get_or_create_ingredient(ingredient_name)
        stmt = select(PantryItem).where(PantryItem.ingredient_id == ingredient.id)
        pantry_item = self.session.exec(stmt).first()

        if pantry_item:
            # Convert to same unit if needed (simplified - assumes same unit)
            pantry_item.quantity_on_hand += quantity
        else:
            pantry_item = PantryItem(
                ingredient_id=ingredient.id,
                quantity_on_hand=quantity,
                unit=unit
            )
            self.session.add(pantry_item)

        self.session.flush()
        return pantry_item

    def consume_from_pantry(self, ingredient_name: str, quantity: float, unit: Unit) -> bool:
        """Consume quantity from pantry. Returns True if sufficient stock."""
        ingredient = self.get_ingredient(ingredient_name)
        if not ingredient:
            return False

        stmt = select(PantryItem).where(PantryItem.ingredient_id == ingredient.id)
        pantry_item = self.session.exec(stmt).first()
        if not pantry_item or pantry_item.quantity_on_hand < quantity:
            return False

        pantry_item.quantity_on_hand -= quantity
        self.session.flush()
        return True

    def get_pantry_item(self, ingredient_name: str) -> Optional[PantryItem]:
        ingredient = self.get_ingredient(ingredient_name)
        if not ingredient:
            return None
        stmt = select(PantryItem).where(PantryItem.ingredient_id == ingredient.id)
        return self.session.exec(stmt).first()

    def list_pantry(self) -> list[PantryItem]:
        stmt = select(PantryItem).join(Ingredient).order_by(Ingredient.name)
        return list(self.session.exec(stmt).all())

    def get_low_stock_items(self) -> list[PantryItem]:
        """Get pantry items below their minimum threshold."""
        stmt = select(PantryItem).where(PantryItem.quantity_on_hand <= PantryItem.minimum_threshold)
        return list(self.session.exec(stmt).all())

    # --- Shopping List Generation ---

    def generate_shopping_list_for_meals(
        self,
        meal_plan_ids: list[int]
    ) -> list[ShoppingList]:
        """Generate consolidated shopping list for given meal plans."""
        # Get all recipe ingredients for these meal plans
        stmt = (
            select(RecipeIngredient, MealPlan.date)
            .join(Recipe, RecipeIngredient.recipe_id == Recipe.id)
            .join(MealPlan, MealPlan.recipe_id == Recipe.id)
            .where(MealPlan.id.in_(meal_plan_ids))
            .where(MealPlan.status.in_([MealStatus.PLANNED, MealStatus.CONFIRMED]))
        )
        results = self.session.exec(stmt).all()

        # Aggregate by ingredient
        aggregated: dict[int, dict] = defaultdict(lambda: {
            "quantity": 0.0,
            "unit": None,
            "meal_plan_ids": [],
            "ingredient": None
        })

        for recipe_ingredient, meal_date in results:
            ingredient_id = recipe_ingredient.ingredient_id
            agg = aggregated[ingredient_id]
            agg["quantity"] += recipe_ingredient.quantity
            agg["unit"] = recipe_ingredient.unit
            agg["meal_plan_ids"].append(meal_plan_ids[0])  # Simplified
            agg["ingredient"] = recipe_ingredient.ingredient

        # Check pantry and create shopping list items
        shopping_items = []
        for ingredient_id, data in aggregated.items():
            ingredient = data["ingredient"]
            needed_qty = data["quantity"]
            unit = data["unit"]

            # Check pantry
            stmt = select(PantryItem).where(PantryItem.ingredient_id == ingredient_id)
            pantry_item = self.session.exec(stmt).first()

            available_qty = pantry_item.quantity_on_hand if pantry_item else 0
            # Simplified unit matching - in reality need conversion
            if pantry_item and pantry_item.unit != unit:
                available_qty = 0  # Can't compare different units easily

            if needed_qty > available_qty and not ingredient.is_staple:
                to_buy = needed_qty - available_qty
                shopping_item = ShoppingList(
                    ingredient_id=ingredient_id,
                    quantity_needed=to_buy,
                    unit=unit,
                    meal_plan_ids=json.dumps(data["meal_plan_ids"])
                )
                self.session.add(shopping_item)
                shopping_items.append(shopping_item)

        self.session.flush()
        return shopping_items

    def get_shopping_list(self, only_unpurchased: bool = True) -> list[ShoppingList]:
        stmt = select(ShoppingList)
        if only_unpurchased:
            stmt = stmt.where(ShoppingList.is_purchased == False)
        stmt = stmt.order_by(ShoppingList.created_at.desc())
        return list(self.session.exec(stmt).all())

    def mark_purchased(self, shopping_list_id: int) -> Optional[ShoppingList]:
        stmt = select(ShoppingList).where(ShoppingList.id == shopping_list_id)
        item = self.session.exec(stmt).first()
        if item:
            item.is_purchased = True
            item.purchased_at = datetime.utcnow()
            # Add to pantry
            self.add_to_pantry(
                item.ingredient.name,
                item.quantity_needed,
                item.unit
            )
            self.session.flush()
        return item

    def clear_shopping_list(self) -> int:
        """Mark all items as purchased and clear."""
        stmt = select(ShoppingList).where(ShoppingList.is_purchased == False)
        items = self.session.exec(stmt).all()
        count = 0
        for item in items:
            item.is_purchased = True
            item.purchased_at = datetime.utcnow()
            self.add_to_pantry(item.ingredient.name, item.quantity_needed, item.unit)
            count += 1
        self.session.flush()
        return count


# Import at bottom to avoid circular
from datetime import datetime