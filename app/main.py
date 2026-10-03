from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from typing import Optional
from datetime import datetime, timedelta, timezone
import os
import structlog

from app.database import init_db, get_session
from app.models import (
    Recipe, MealPlan,
    PantryItem, ShoppingList,
    Ingredient, EntreeType, MealStatus, Unit
)
from app.services.recipe import RecipeService
from app.services.pantry import PantryService
from app.services.notion import NotionService
from app.scheduler.jobs import MealPlannerScheduler, run_async_job
from app.bot.telegram_bot import TelegramBotService
from app.schemas import (
    RecipeCreate, RecipeUpdate,
    PantryItemCreate, PantryItemUpdate,
    MealPlanGenerate, MealPlanReplace,
    ShoppingListGenerate, NotionHarvest
)

logger = structlog.get_logger()

# Global instances
telegram_bot: Optional[TelegramBotService] = None
scheduler: Optional[MealPlannerScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_bot, scheduler

    # Startup
    logger.info("Starting Meal Planner API")
    init_db()

    # Initialize Telegram bot
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        telegram_bot = TelegramBotService()
        await telegram_bot.initialize()
        await telegram_bot.start_polling()

        # Initialize scheduler with bot
        scheduler = MealPlannerScheduler(telegram_bot)
        scheduler.start()

        logger.info("Telegram bot and scheduler started")
    else:
        logger.warning("Telegram credentials not set - bot disabled")

    yield

    # Shutdown
    logger.info("Shutting down Meal Planner API")
    if scheduler:
        scheduler.shutdown()
    if telegram_bot:
        await telegram_bot.stop()


app = FastAPI(
    title="Meal Planner API",
    description="Automated meal planning with pantry management and Telegram delivery",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Dependency ---

def get_recipe_service() -> RecipeService:
    return RecipeService(get_session())


def get_pantry_service() -> PantryService:
    return PantryService(get_session())


def get_notion_service() -> NotionService:
    return NotionService(get_session())


# --- Health ---

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# --- Recipe Endpoints ---

@app.post("/recipes", response_model=Recipe)
def create_recipe(recipe: RecipeCreate, svc: RecipeService = Depends(get_recipe_service)):
    """Create a new recipe."""
    created = svc.create_recipe(
        name=recipe.name,
        entree_type=recipe.entree_type,
        instructions=recipe.instructions,
        prep_time_minutes=recipe.prep_time_minutes,
        cook_time_minutes=recipe.cook_time_minutes,
        servings=recipe.servings,
        ingredients=recipe.ingredients,
        description=recipe.description,
        source_url=recipe.source_url,
        tags=recipe.tags
    )
    return created


@app.get("/recipes", response_model=list[Recipe])
def list_recipes(entree: Optional[EntreeType] = None, svc: RecipeService = Depends(get_recipe_service)):
    """List all recipes, optionally filtered by entree type."""
    if entree:
        return svc.get_recipes_by_entree(entree)
    return svc.list_all_recipes()


@app.get("/recipes/search")
def search_recipes(q: str, svc: RecipeService = Depends(get_recipe_service)):
    """Search recipes by name."""
    return svc.search_recipes(q)


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int, svc: RecipeService = Depends(get_recipe_service)):
    """Get recipe with full ingredient details."""
    detail = svc.get_recipe_with_ingredients(recipe_id)
    if not detail:
        raise HTTPException(404, "Recipe not found")
    return detail


@app.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: int, svc: RecipeService = Depends(get_recipe_service)):
    """Delete a recipe."""
    if not svc.delete_recipe(recipe_id):
        raise HTTPException(404, "Recipe not found")
    return {"ok": True}


# --- Meal Plan Endpoints ---

@app.post("/meal-plans/generate")
def generate_meal_plan(
    start_date: datetime,
    days: int = 7,
    allowed_entrees: Optional[list[EntreeType]] = None,
    svc: RecipeService = Depends(get_recipe_service)
):
    """Generate meal plan for date range."""
    meal_plans = svc.generate_meal_plan(start_date, days, allowed_entrees)

    # Generate shopping list using the same session
    mp_ids = [mp.id for mp in meal_plans]
    pantry_svc = PantryService(svc.session)
    pantry_svc.generate_shopping_list_for_meals(mp_ids)

    # Commit the session
    svc.session.commit()

    return {"meal_plans": meal_plans, "count": len(meal_plans)}


@app.get("/meal-plans/today")
def get_today_meal_plan(svc: RecipeService = Depends(get_recipe_service)):
    """Get today's meal plan with full recipe details."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    mp = svc.get_meal_plan(today)
    if not mp:
        raise HTTPException(404, "No meal plan for today")
    detail = svc.get_recipe_with_ingredients(mp.recipe_id)
    return {"meal_plan": mp, "recipe": detail}


@app.get("/meal-plans/week")
def get_week_meal_plan(svc: RecipeService = Depends(get_recipe_service)):
    """Get this week's meal plans."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    week_end = today.replace(hour=23, minute=59, second=59) + timedelta(days=6)
    meals = svc.get_meal_plans_range(today, week_end)
    return {"meal_plans": meals}


@app.post("/meal-plans/{meal_plan_id}/confirm")
def confirm_meal_plan(meal_plan_id: int, svc: RecipeService = Depends(get_recipe_service)):
    """Confirm a meal plan."""
    mp = svc.confirm_meal_plan(meal_plan_id)
    if not mp:
        raise HTTPException(404, "Meal plan not found")
    return mp


@app.post("/meal-plans/{meal_plan_id}/replace")
def replace_meal_plan(
    meal_plan_id: int,
    new_recipe_id: Optional[int] = None,
    reason: Optional[str] = None,
    svc: RecipeService = Depends(get_recipe_service)
):
    """Replace a meal plan with alternative."""
    mp = svc.replace_meal_plan(meal_plan_id, reason, new_recipe_id)
    if not mp:
        raise HTTPException(404, "Meal plan not found or no alternatives")
    return mp


@app.post("/meal-plans/{meal_plan_id}/cook")
def mark_cooked(meal_plan_id: int, svc: RecipeService = Depends(get_recipe_service)):
    """Mark meal as cooked (consumes pantry ingredients)."""
    mp = svc.mark_cooked(meal_plan_id)
    if not mp:
        raise HTTPException(404, "Meal plan not found")
    return mp


@app.post("/meal-plans/{meal_plan_id}/skip")
def skip_meal_plan(meal_plan_id: int, svc: RecipeService = Depends(get_recipe_service)):
    """Skip a meal plan."""
    mp = svc.skip_meal_plan(meal_plan_id)
    if not mp:
        raise HTTPException(404, "Meal plan not found")
    return mp


# --- Pantry Endpoints ---

@app.get("/pantry")
def list_pantry(svc: PantryService = Depends(get_pantry_service)):
    """List all pantry items."""
    return svc.list_pantry()


@app.get("/pantry/low-stock")
def low_stock(svc: PantryService = Depends(get_pantry_service)):
    """Get items below minimum threshold."""
    return svc.get_low_stock_items()


@app.post("/pantry")
def add_to_pantry(item: PantryItemCreate, svc: PantryService = Depends(get_pantry_service)):
    """Add or update pantry item."""
    result = svc.set_pantry_quantity(item.name, item.quantity, item.unit, item.minimum_threshold)
    return result


@app.post("/pantry/consume")
def consume_from_pantry(name: str, quantity: float, unit: Unit, svc: PantryService = Depends(get_pantry_service)):
    """Consume from pantry."""
    success = svc.consume_from_pantry(name, quantity, unit)
    if not success:
        raise HTTPException(400, "Insufficient stock or item not found")
    return {"ok": True}


# --- Shopping List Endpoints ---

@app.get("/shopping")
def get_shopping_list(svc: PantryService = Depends(get_pantry_service)):
    """Get current shopping list."""
    return svc.get_shopping_list()


@app.post("/shopping/generate")
def generate_shopping_list(
    meal_plan_ids: list[int],
    svc: PantryService = Depends(get_pantry_service)
):
    """Generate shopping list for meal plans."""
    items = svc.generate_shopping_list_for_meals(meal_plan_ids)
    return {"items": items, "count": len(items)}


@app.post("/shopping/{item_id}/purchase")
def mark_purchased(item_id: int, svc: PantryService = Depends(get_pantry_service)):
    """Mark shopping item as purchased (adds to pantry)."""
    item = svc.mark_purchased(item_id)
    if not item:
        raise HTTPException(404, "Shopping item not found")
    return item


@app.post("/shopping/clear")
def clear_shopping_list(svc: PantryService = Depends(get_pantry_service)):
    """Mark all items purchased and add to pantry."""
    count = svc.clear_shopping_list()
    return {"purchased_count": count}


# --- Notion Endpoints ---

@app.post("/notion/push-recipe/{recipe_id}")
def push_recipe_to_notion(recipe_id: int, svc: NotionService = Depends(get_notion_service)):
    """Push a recipe to Notion."""
    page_id = svc.push_recipe_to_notion(recipe_id)
    if not page_id:
        raise HTTPException(404, "Recipe not found")
    return {"notion_page_id": page_id}


@app.post("/notion/harvest")
def harvest_to_notion(days_back: int = 7, svc: NotionService = Depends(get_notion_service)):
    """Harvest cooked meals to Notion."""
    harvested = svc.harvest_cooked_meals(days_back)
    return {"harvested": harvested, "count": len(harvested)}


@app.get("/notion/search")
def search_notion(q: str, svc: NotionService = Depends(get_notion_service)):
    """Search Notion for recipes."""
    return svc.search_notion_recipes(q)


@app.post("/notion/pull/{page_id}")
def pull_from_notion(page_id: str, svc: NotionService = Depends(get_notion_service)):
    """Pull a recipe from Notion."""
    recipe = svc.pull_recipe_from_notion(page_id)
    if not recipe:
        raise HTTPException(404, "Failed to pull recipe")
    return recipe


# --- Scheduler Control ---

@app.post("/scheduler/trigger/{job_id}")
def trigger_job(job_id: str):
    """Manually trigger a scheduled job."""
    if not scheduler:
        raise HTTPException(503, "Scheduler not running")

    job = scheduler.scheduler.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")

    job.func()
    return {"triggered": job_id}


@app.get("/scheduler/jobs")
def list_jobs():
    """List all scheduled jobs."""
    if not scheduler:
        return {"jobs": []}

    jobs = []
    for job in scheduler.scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        })
    return {"jobs": jobs}