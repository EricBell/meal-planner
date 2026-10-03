from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import os
import asyncio
from app.services.recipe import RecipeService
from app.services.pantry import PantryService
from app.services.notion import NotionService
from app.bot.telegram_bot import TelegramBotService
from app.database import get_session_sync
from app.models import EntreeType, MealStatus
import structlog

logger = structlog.get_logger()


class MealPlannerScheduler:
    """APScheduler jobs for meal planning automation."""

    def __init__(self, telegram_bot: TelegramBotService):
        self.bot = telegram_bot
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Configure scheduled jobs from environment."""
        delivery_hour = int(os.getenv("MORNING_DELIVERY_HOUR", "8"))
        delivery_minute = int(os.getenv("MORNING_DELIVERY_MINUTE", "0"))
        harvest_day = os.getenv("WEEKLY_HARVEST_DAY", "sunday")
        harvest_hour = int(os.getenv("WEEKLY_HARVEST_HOUR", "10"))

        # Daily meal plan generation (runs at midnight)
        self.scheduler.add_job(
            self.generate_daily_meal_plan,
            CronTrigger(hour=0, minute=5),
            id="generate_meal_plan",
            name="Generate next day's meal plan",
            replace_existing=True
        )

        # Morning delivery
        self.scheduler.add_job(
            self.deliver_morning_meal,
            CronTrigger(hour=delivery_hour, minute=delivery_minute),
            id="morning_delivery",
            name="Deliver morning meal plan",
            replace_existing=True
        )

        # Weekly Notion harvest
        self.scheduler.add_job(
            self.harvest_to_notion,
            CronTrigger(day_of_week=harvest_day, hour=harvest_hour, minute=0),
            id="weekly_harvest",
            name="Weekly Notion harvest",
            replace_existing=True
        )

        # Weekly meal plan generation (every Sunday for the week)
        self.scheduler.add_job(
            self.generate_weekly_meal_plan,
            CronTrigger(day_of_week="sun", hour=1, minute=0),
            id="weekly_meal_plan",
            name="Generate weekly meal plan",
            replace_existing=True
        )

        logger.info("Scheduler jobs configured",
                    delivery_time=f"{delivery_hour}:{delivery_minute:02d}",
                    harvest_day=harvest_day,
                    harvest_hour=harvest_hour)

    def start(self):
        self.scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    # --- Job Functions ---

    def generate_daily_meal_plan(self):
        """Generate meal plan for tomorrow if not exists."""
        logger.info("Running daily meal plan generation")
        tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        with RecipeService(get_session_sync()) as svc:
            existing = svc.get_meal_plan(tomorrow)
            if existing:
                logger.info("Meal plan already exists for tomorrow", date=tomorrow.date())
                return

            # Generate single day
            meal_plans = svc.generate_meal_plan(
                start_date=tomorrow,
                days=1,
                allowed_entrees=list(EntreeType)
            )

        logger.info("Generated daily meal plan", count=len(meal_plans))

    def generate_weekly_meal_plan(self):
        """Generate meal plan for the next 7 days."""
        logger.info("Running weekly meal plan generation")
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Get allowed entrees from env or use all
        allowed_str = os.getenv("DEFAULT_ENTREES", "")
        if allowed_str:
            allowed_entrees = [EntreeType(e.strip()) for e in allowed_str.split(",")]
        else:
            allowed_entrees = list(EntreeType)

        with RecipeService(get_session_sync()) as svc:
            meal_plans = svc.generate_meal_plan(
                start_date=start_date,
                days=7,
                allowed_entrees=allowed_entrees,
                avoid_recent_days=14
            )

        # Generate shopping list for the week
        mp_ids = [mp.id for mp in meal_plans]
        with PantryService(get_session_sync()) as pantry:
            pantry.generate_shopping_list_for_meals(mp_ids)

        logger.info("Generated weekly meal plan", count=len(meal_plans))

    async def deliver_morning_meal(self):
        """Deliver today's meal plan via Telegram."""
        logger.info("Running morning meal delivery")
        try:
            await self.bot.deliver_morning_meal_plan()
            logger.info("Morning delivery sent")
        except Exception as e:
            logger.error("Failed to deliver morning meal", error=str(e))

    def harvest_to_notion(self):
        """Harvest cooked meals to Notion."""
        logger.info("Running weekly Notion harvest")
        try:
            with NotionService(get_session_sync()) as svc:
                harvested = svc.harvest_cooked_meals(days_back=7)
            logger.info("Notion harvest complete", count=len(harvested))
        except Exception as e:
            logger.error("Notion harvest failed", error=str(e))


# Sync wrapper for APScheduler (which runs sync functions)
def run_async_job(coro):
    """Run async coroutine in sync context for APScheduler."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)