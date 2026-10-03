from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from app.services.recipe import RecipeService
from app.services.pantry import PantryService
from app.services.notion import NotionService
from app.models import MealPlan, MealStatus, EntreeType, Recipe
from app.database import get_session_sync
from datetime import datetime, timedelta
import os
import json


class TelegramBotService:
    """Telegram bot for meal plan delivery and interaction."""

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.app: Optional[Application] = None

    async def initialize(self):
        """Initialize the bot application."""
        self.app = Application.builder().token(self.token).build()
        self._register_handlers()

    def _register_handlers(self):
        """Register command and callback handlers."""
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("today", self.cmd_today))
        self.app.add_handler(CommandHandler("week", self.cmd_week))
        self.app.add_handler(CommandHandler("shopping", self.cmd_shopping))
        self.app.add_handler(CommandHandler("pantry", self.cmd_pantry))
        self.app.add_handler(CommandHandler("add_pantry", self.cmd_add_pantry))
        self.app.add_handler(CommandHandler("replace", self.cmd_replace))
        self.app.add_handler(CommandHandler("search", self.cmd_search))
        self.app.add_handler(CommandHandler("harvest", self.cmd_harvest))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

    async def start_polling(self):
        """Start the bot."""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self):
        """Stop the bot."""
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    # --- Command Handlers ---

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message."""
        await update.message.reply_text(
            "🍽️ *Meal Planner Bot*\n\n"
            "Commands:\n"
            "/today - Get today's meal plan\n"
            "/week - View this week's meal plan\n"
            "/shopping - View shopping list\n"
            "/pantry - View pantry inventory\n"
            "/add_pantry <item> <qty> <unit> - Add to pantry\n"
            "/replace <date> - Replace a meal\n"
            "/search <query> - Search recipes\n"
            "/harvest - Sync cooked meals to Notion\n"
            "/help - Show this help",
            parse_mode="Markdown"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_start(update, context)

    async def cmd_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show today's meal plan."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        with RecipeService(get_session_sync()) as svc:
            mp = svc.get_meal_plan(today)

        if not mp:
            await update.message.reply_text("No meal planned for today. Run meal planning first.")
            return

        recipe_detail = self._get_recipe_detail(mp.recipe_id)
        if not recipe_detail:
            await update.message.reply_text("Recipe not found.")
            return

        msg = self._format_meal_plan(mp, recipe_detail, "Today")
        keyboard = self._meal_plan_keyboard(mp.id)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    async def cmd_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show this week's meal plan."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today + timedelta(days=6)

        with RecipeService(get_session_sync()) as svc:
            meals = svc.get_meal_plans_range(today, week_end)

        if not meals:
            await update.message.reply_text("No meals planned this week.")
            return

        msg = "📅 *This Week's Meal Plan*\n\n"
        for mp in meals:
            recipe_detail = self._get_recipe_detail(mp.recipe_id)
            if recipe_detail:
                day_name = mp.date.strftime("%a %m/%d")
                status_emoji = self._status_emoji(mp.status)
                msg += f"{status_emoji} *{day_name}*: {recipe_detail['name']} ({recipe_detail['entree_type']})\n"

        await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_shopping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show shopping list."""
        with PantryService(get_session_sync()) as svc:
            items = svc.get_shopping_list(only_unpurchased=True)

        if not items:
            await update.message.reply_text("🛒 Shopping list is empty!")
            return

        msg = "🛒 *Shopping List*\n\n"
        for item in items:
            msg += f"• {item.ingredient.name}: {item.quantity_needed} {item.unit.value}\n"

        keyboard = [[InlineKeyboardButton("✅ Mark All Purchased", callback_data="shopping_mark_all")]]
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def cmd_pantry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pantry inventory."""
        with PantryService(get_session_sync()) as svc:
            items = svc.list_pantry()

        if not items:
            await update.message.reply_text("🏠 Pantry is empty. Add items with `/add_pantry`.")
            return

        msg = "🏠 *Pantry Inventory*\n\n"
        for item in items:
            status = "⚠️ LOW" if item.quantity_on_hand <= item.minimum_threshold else "✅"
            msg += f"{status} {item.ingredient.name}: {item.quantity_on_hand} {item.unit.value}\n"

        await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_add_pantry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add item to pantry: /add_pantry chicken 2 kg"""
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("Usage: `/add_pantry <item> <quantity> <unit>`\nExample: `/add_pantry chicken 2 kg`")
            return

        name = args[0]
        try:
            qty = float(args[1])
        except ValueError:
            await update.message.reply_text("Quantity must be a number.")
            return

        unit_str = args[2].lower()
        try:
            from app.models import Unit
            unit = Unit(unit_str)
        except ValueError:
            await update.message.reply_text(f"Invalid unit. Use: {', '.join([u.value for u in Unit])}")
            return

        with PantryService(get_session_sync()) as svc:
            svc.add_to_pantry(name, qty, unit)

        await update.message.reply_text(f"✅ Added {qty} {unit.value} of {name} to pantry.")

    async def cmd_replace(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Replace a meal: /replace 2024-01-15"""
        args = context.args
        if not args:
            await update.message.reply_text("Usage: `/replace <YYYY-MM-DD>`")
            return

        try:
            date = datetime.strptime(args[0], "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text("Invalid date format. Use YYYY-MM-DD.")
            return

        with RecipeService(get_session_sync()) as svc:
            mp = svc.get_meal_plan(date)

        if not mp:
            await update.message.reply_text(f"No meal planned for {args[0]}.")
            return

        # Show alternatives
        recipe = self._get_recipe_detail(mp.recipe_id)
        if not recipe:
            await update.message.reply_text("Recipe not found.")
            return

        with RecipeService(get_session_sync()) as svc:
            alternatives = svc.get_recipes_by_entree(recipe["entree_type"])
            alternatives = [r for r in alternatives if r.id != mp.recipe_id]

        if not alternatives:
            await update.message.reply_text("No alternative recipes for this entree type.")
            return

        keyboard = []
        for alt in alternatives[:5]:
            keyboard.append([InlineKeyboardButton(
                f"{alt.name} ({alt.prep_time_minutes}+{alt.cook_time_minutes}min)",
                callback_data=f"replace_{mp.id}_{alt.id}"
            )])

        msg = f"🔄 *Replace {recipe['name']} ({args[0]})*\n\nChoose an alternative:"
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Search recipes locally and in Notion."""
        query = " ".join(context.args) if context.args else ""
        if not query:
            await update.message.reply_text("Usage: `/search <query>`")
            return

        # Search local
        with RecipeService(get_session_sync()) as svc:
            local = svc.search_recipes(query)

        # Search Notion
        with NotionService(get_session_sync()) as svc:
            notion = svc.search_notion_recipes(query)

        msg = f"🔍 *Search results for '{query}'*\n\n"

        if local:
            msg += "*Local Recipes:*\n"
            for r in local[:5]:
                msg += f"• {r.name} ({r.entree_type.value}) - {r.prep_time_minutes}+{r.cook_time_minutes}min\n"

        if notion:
            msg += "\n*Notion Recipes:*\n"
            for r in notion[:5]:
                msg += f"• {r['name']} ({r['entree_type']}) - [Open in Notion]({r['url']})\n"

        if not local and not notion:
            msg += "No results found."

        await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)

    async def cmd_harvest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Harvest cooked meals to Notion."""
        await update.message.reply_text("🌾 Harvesting cooked meals to Notion...")

        with NotionService(get_session_sync()) as svc:
            harvested = svc.harvest_cooked_meals(days_back=30)

        if not harvested:
            await update.message.reply_text("No new cooked meals to harvest.")
            return

        msg = f"✅ Harvested {len(harvested)} meals to Notion:\n\n"
        for h in harvested:
            msg += f"• {h['recipe_name']} ({h['date'][:10]})\n"

        await update.message.reply_text(msg)

    # --- Callback Handler ---

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data

        if data.startswith("replace_"):
            _, mp_id_str, recipe_id_str = data.split("_")
            mp_id = int(mp_id_str)
            recipe_id = int(recipe_id_str)

            with RecipeService(get_session_sync()) as svc:
                mp = svc.replace_meal_plan(mp_id, new_recipe_id=recipe_id)

            if mp:
                new_recipe = self._get_recipe_detail(recipe_id)
                await query.edit_message_text(
                    f"✅ Replaced with *{new_recipe['name']}*",
                    parse_mode="Markdown"
                )

        elif data == "shopping_mark_all":
            with PantryService(get_session_sync()) as svc:
                count = svc.clear_shopping_list()
            await query.edit_message_text(f"✅ Marked {count} items as purchased and added to pantry.")

        elif data.startswith("confirm_"):
            mp_id = int(data.split("_")[1])
            with RecipeService(get_session_sync()) as svc:
                svc.confirm_meal_plan(mp_id)
            await query.edit_message_text("✅ Meal confirmed!")

        elif data.startswith("skip_"):
            mp_id = int(data.split("_")[1])
            with RecipeService(get_session_sync()) as svc:
                svc.skip_meal_plan(mp_id)
            await query.edit_message_text("⏭️ Meal skipped.")

    # --- Text Handler ---

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language requests."""
        text = update.message.text.lower()

        if "what" in text and ("dinner" in text or "meal" in text or "cook" in text):
            await self.cmd_today(update, context)
        elif "shopping" in text or "buy" in text or "grocery" in text:
            await self.cmd_shopping(update, context)
        elif "pantry" in text or "inventory" in text or "have" in text:
            await self.cmd_pantry(update, context)
        else:
            await update.message.reply_text(
                "I didn't understand. Try:\n"
                "• 'What's for dinner?'\n"
                "• 'Show shopping list'\n"
                "• 'What's in the pantry?'\n"
                "• Or use /help for commands"
            )

    # --- Delivery Methods ---

    async def deliver_morning_meal_plan(self):
        """Send morning delivery of today's meal plan."""
        if not self.app or not self.chat_id:
            return

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        with RecipeService(get_session_sync()) as svc:
            mp = svc.get_meal_plan(today)

        if not mp:
            return

        recipe_detail = self._get_recipe_detail(mp.recipe_id)
        if not recipe_detail:
            return

        msg = self._format_meal_plan(mp, recipe_detail, "Good morning! 🌅 Today's dinner")
        keyboard = self._meal_plan_keyboard(mp.id)

        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    def _get_recipe_detail(self, recipe_id: int) -> Optional[dict]:
        with RecipeService(get_session_sync()) as svc:
            return svc.get_recipe_with_ingredients(recipe_id)

    def _format_meal_plan(self, mp: MealPlan, recipe: dict, title: str) -> str:
        status_emoji = self._status_emoji(mp.status)

        msg = f"{status_emoji} *{title}*\n\n"
        msg += f"*{recipe['name']}* ({recipe['entree_type'].title()})\n"
        msg += f"⏱️ Prep: {recipe['prep_time_minutes']}min | Cook: {recipe['cook_time_minutes']}min | Servings: {recipe['servings']}\n\n"

        if recipe['description']:
            msg += f"{recipe['description']}\n\n"

        msg += "*Ingredients:*\n"
        for ing in recipe['ingredients']:
            staple_mark = " 🏠" if ing['is_staple'] else ""
            optional_mark = " *(optional)*" if ing['is_optional'] else ""
            msg += f"• {ing['quantity']} {ing['unit']} {ing['name']}{staple_mark}{optional_mark}\n"

        msg += f"\n*Instructions:*\n{recipe['instructions']}"

        return msg

    def _meal_plan_keyboard(self, mp_id: int) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{mp_id}"),
                InlineKeyboardButton("🔄 Replace", callback_data=f"replace_prompt_{mp_id}"),
                InlineKeyboardButton("⏭️ Skip", callback_data=f"skip_{mp_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def _status_emoji(self, status: MealStatus) -> str:
        return {
            MealStatus.PLANNED: "📋",
            MealStatus.CONFIRMED: "✅",
            MealStatus.COOKED: "🍽️",
            MealStatus.SKIPPED: "⏭️",
            MealStatus.REPLACED: "🔄"
        }.get(status, "❓")