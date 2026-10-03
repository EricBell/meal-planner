from typing import Optional
from notion_client import Client
from notion_client.errors import APIResponseError
from app.models import Recipe, MealPlan, PantryItem, Ingredient, NotionSyncLog
from app.database import get_session_sync
from sqlmodel import Session, select
from datetime import datetime
import json
import os
from tenacity import retry, stop_after_attempt, wait_exponential


class NotionService:
    """Sync recipes and meal plans to/from Notion."""

    def __init__(self, session: Session):
        self._session = session
        self._client = None

    @property
    def client(self) -> Client:
        if not self._client:
            self._client = Client(auth=os.getenv("NOTION_TOKEN"))
        return self._client

    @property
    def session(self) -> Session:
        return self._session

    def _log_sync(
        self,
        sync_type: str,
        entity_type: str,
        entity_id: int,
        notion_page_id: str,
        status: str,
        error_message: str = None
    ):
        log = NotionSyncLog(
            sync_type=sync_type,
            entity_type=entity_type,
            entity_id=entity_id,
            notion_page_id=notion_page_id,
            status=status,
            error_message=error_message
        )
        self.session.add(log)
        self.session.flush()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _create_page(self, database_id: str, properties: dict, children: list = None) -> str:
        """Create a Notion page and return its ID."""
        response = self.client.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=children or []
        )
        return response["id"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _update_page(self, page_id: str, properties: dict, children: list = None):
        """Update a Notion page."""
        self.client.pages.update(page_id=page_id, properties=properties)
        if children:
            # Clear existing blocks and add new ones
            blocks = self.client.blocks.children.list(block_id=page_id)
            for block in blocks["results"]:
                self.client.blocks.delete(block_id=block["id"])
            self.client.blocks.children.append(block_id=page_id, children=children)

    def _recipe_to_notion_properties(self, recipe: Recipe, ingredients: list) -> dict:
        """Convert recipe to Notion properties."""
        props = {
            "Name": {"title": [{"text": {"content": recipe.name}}]},
            "Entree Type": {"select": {"name": recipe.entree_type.value}},
            "Prep Time (min)": {"number": recipe.prep_time_minutes},
            "Cook Time (min)": {"number": recipe.cook_time_minutes},
            "Servings": {"number": recipe.servings},
            "Status": {"select": {"name": "Active"}},
        }

        if recipe.description:
            props["Description"] = {"rich_text": [{"text": {"content": recipe.description}}]}

        if recipe.source_url:
            props["Source URL"] = {"url": recipe.source_url}

        if recipe.tags:
            props["Tags"] = {"multi_select": [{"name": t} for t in json.loads(recipe.tags)]}

        return props

    def _recipe_to_notion_blocks(self, recipe: Recipe, ingredients: list) -> list:
        """Convert recipe to Notion blocks (content)."""
        blocks = []

        # Ingredients heading
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Ingredients"}}]}
        })

        # Ingredients as bullet list
        for ing in ingredients:
            qty_str = f"{ing['quantity']} {ing['unit']}"
            if ing.get("notes"):
                qty_str += f" ({ing['notes']})"
            if ing.get("is_optional"):
                qty_str += " *optional*"
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"text": {"content": f"{ing['name']}: {qty_str}"}}]
                }
            })

        # Instructions heading
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Instructions"}}]}
        })

        # Instructions as numbered list
        for i, step in enumerate(recipe.instructions.split("\n"), 1):
            if step.strip():
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"text": {"content": step.strip()}}]
                    }
                })

        return blocks

    def push_recipe_to_notion(self, recipe_id: int) -> Optional[str]:
        """Push a recipe to Notion. Returns Notion page ID."""
        database_id = os.getenv("NOTION_DATABASE_ID")
        if not database_id:
            raise ValueError("NOTION_DATABASE_ID not set")

        recipe = self.session.get(Recipe, recipe_id)
        if not recipe:
            return None

        # Get ingredients
        stmt = select(RecipeIngredient, Ingredient).join(Ingredient).where(
            RecipeIngredient.recipe_id == recipe_id
        )
        results = self.session.exec(stmt).all()
        ingredients = [
            {
                "name": ing.name,
                "quantity": ri.quantity,
                "unit": ri.unit.value,
                "notes": ri.notes,
                "is_optional": ri.is_optional
            }
            for ri, ing in results
        ]

        try:
            if recipe.source_notion_page_id:
                # Update existing
                self._update_page(
                    recipe.source_notion_page_id,
                    self._recipe_to_notion_properties(recipe, ingredients),
                    self._recipe_to_notion_blocks(recipe, ingredients)
                )
                notion_page_id = recipe.source_notion_page_id
            else:
                # Create new
                notion_page_id = self._create_page(
                    database_id,
                    self._recipe_to_notion_properties(recipe, ingredients),
                    self._recipe_to_notion_blocks(recipe, ingredients)
                )
                recipe.source_notion_page_id = notion_page_id
                self.session.add(recipe)

            self._log_sync("push", "recipe", recipe_id, notion_page_id, "success")
            self.session.flush()
            return notion_page_id

        except APIResponseError as e:
            self._log_sync("push", "recipe", recipe_id, "", "failed", str(e))
            raise

    def harvest_cooked_meals(self, days_back: int = 7) -> list[dict]:
        """Harvest recently cooked meals and push to Notion."""
        cutoff = datetime.utcnow() - timedelta(days=days_back)

        stmt = select(MealPlan).where(
            MealPlan.date >= cutoff,
            MealPlan.status == MealStatus.COOKED
        )
        meal_plans = self.session.exec(stmt).all()

        harvested = []
        for mp in meal_plans:
            recipe = self.session.get(Recipe, mp.recipe_id)
            if not recipe:
                continue

            # Check if already synced
            stmt = select(NotionSyncLog).where(
                NotionSyncLog.entity_type == "meal_plan",
                NotionSyncLog.entity_id == mp.id,
                NotionSyncLog.status == "success"
            )
            existing = self.session.exec(stmt).first()
            if existing:
                continue

            # Push recipe if not already
            if not recipe.source_notion_page_id:
                self.push_recipe_to_notion(recipe.id)

            # Create meal plan entry in Notion (could be separate DB or same)
            # For now, just log the harvest
            self._log_sync("harvest", "meal_plan", mp.id, recipe.source_notion_page_id or "", "success")

            harvested.append({
                "meal_plan_id": mp.id,
                "recipe_name": recipe.name,
                "date": mp.date.isoformat(),
                "notion_page_id": recipe.source_notion_page_id
            })

        return harvested

    def search_notion_recipes(self, query: str) -> list[dict]:
        """Search Notion database for recipes matching query."""
        database_id = os.getenv("NOTION_DATABASE_ID")
        if not database_id:
            return []

        try:
            response = self.client.databases.query(
                database_id=database_id,
                filter={
                    "property": "Name",
                    "title": {"contains": query}
                },
                page_size=20
            )

            results = []
            for page in response["results"]:
                props = page["properties"]
                name = ""
                if props.get("Name", {}).get("title"):
                    name = props["Name"]["title"][0]["text"]["content"]

                entree = ""
                if props.get("Entree Type", {}).get("select"):
                    entree = props["Entree Type"]["select"]["name"]

                results.append({
                    "notion_page_id": page["id"],
                    "name": name,
                    "entree_type": entree,
                    "url": page["url"]
                })

            return results

        except APIResponseError:
            return []

    def pull_recipe_from_notion(self, notion_page_id: str) -> Optional[Recipe]:
        """Pull a recipe from Notion and create/update local copy."""
        try:
            page = self.client.pages.retrieve(page_id=notion_page_id)
            blocks = self.client.blocks.children.list(block_id=notion_page_id)
            props = page["properties"]

            # Parse properties
            name = ""
            if props.get("Name", {}).get("title"):
                name = props["Name"]["title"][0]["text"]["content"]

            entree_str = ""
            if props.get("Entree Type", {}).get("select"):
                entree_str = props["Entree Type"]["select"]["name"]

            prep_time = props.get("Prep Time (min)", {}).get("number", 0)
            cook_time = props.get("Cook Time (min)", {}).get("number", 0)
            servings = props.get("Servings", {}).get("number", 4)

            # Parse ingredients from blocks
            ingredients = []
            instructions = []
            current_section = None

            for block in blocks["results"]:
                if block["type"] == "heading_2":
                    heading_text = ""
                    for rt in block["heading_2"]["rich_text"]:
                        heading_text += rt["text"]["content"]
                    if "ingredient" in heading_text.lower():
                        current_section = "ingredients"
                    elif "instruction" in heading_text.lower():
                        current_section = "instructions"
                elif block["type"] == "bulleted_list_item" and current_section == "ingredients":
                    text = ""
                    for rt in block["bulleted_list_item"]["rich_text"]:
                        text += rt["text"]["content"]
                    # Parse "name: qty unit (notes)"
                    if ":" in text:
                        name_part, qty_part = text.split(":", 1)
                        ingredients.append({
                            "name": name_part.strip(),
                            "raw_quantity": qty_part.strip()
                        })
                elif block["type"] == "numbered_list_item" and current_section == "instructions":
                    text = ""
                    for rt in block["numbered_list_item"]["rich_text"]:
                        text += rt["text"]["content"]
                    instructions.append(text)

            # Check if recipe already exists locally
            stmt = select(Recipe).where(Recipe.source_notion_page_id == notion_page_id)
            recipe = self.session.exec(stmt).first()

            if not recipe:
                # Need to parse entree type
                try:
                    from app.models import EntreeType
                    entree_type = EntreeType(entree_str.lower())
                except ValueError:
                    entree_type = EntreeType.CHICKEN  # default

                recipe = Recipe(
                    name=name,
                    entree_type=entree_type,
                    instructions="\n".join(instructions),
                    prep_time_minutes=prep_time,
                    cook_time_minutes=cook_time,
                    servings=servings,
                    source_notion_page_id=notion_page_id
                )
                self.session.add(recipe)
                self.session.flush()

                # Add ingredients
                for ing_data in ingredients:
                    # Simplified parsing - would need improvement
                    ingredient = self._get_or_create_ingredient(ing_data["name"])
                    # Parse quantity/unit from raw_quantity
                    ri = RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_id=ingredient.id,
                        quantity=1.0,  # Would parse from raw_quantity
                        unit=Unit.GRAMS
                    )
                    self.session.add(ri)

                self.session.flush()

            self._log_sync("pull", "recipe", recipe.id, notion_page_id, "success")
            return recipe

        except APIResponseError as e:
            self._log_sync("pull", "recipe", 0, notion_page_id, "failed", str(e))
            return None

    def _get_or_create_ingredient(self, name: str) -> Ingredient:
        stmt = select(Ingredient).where(Ingredient.name == name.lower().strip())
        ingredient = self.session.exec(stmt).first()
        if not ingredient:
            ingredient = Ingredient(name=name.lower().strip())
            self.session.add(ingredient)
            self.session.flush()
        return ingredient


# Import at bottom
from datetime import timedelta
from app.models import Unit, EntreeType, RecipeIngredient, MealStatus