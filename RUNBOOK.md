# Meal Planner — Operations Runbook

> **Version:** 1.0  
> **Repo:** https://github.com/EricBell/meal-planner  
> **Last Updated:** 2026-10-03  
> **Author:** Hermes Agent

---

## 1. System Overview

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Telegram Bot  │────▶│  Meal Planner    │────▶│    Notion DB    │
│  (Commands +    │     │  (FastAPI +      │     │  (Recipes +     │
│   Morning Push) │     │   APScheduler)   │     │   History)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   SQLite/Postgres│
                       │  (Recipes, Plans,│
                       │   Pantry, Shop)  │
                       └──────────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| API Server | FastAPI + Uvicorn | REST endpoints for recipes, meal plans, pantry |
| Telegram Bot | python-telegram-bot v22 | Morning delivery, interactive commands |
| Scheduler | APScheduler (AsyncIOScheduler) | Daily planning, morning push, weekly harvest |
| Database | SQLModel + SQLite (default) / PostgreSQL | Persistent storage |
| Notion Sync | notion-client | Bi-directional recipe/history sync |
| Pantry Service | Custom | Inventory tracking, shopping list generation |

### Scheduled Jobs

| Job ID | Schedule | Description |
|--------|----------|-------------|
| `generate_meal_plan` | Daily 00:05 | Plan tomorrow if missing |
| `weekly_meal_plan` | Sunday 01:00 | Plan full week + shopping list |
| `morning_delivery` | Daily 08:00 | Send today's recipe via Telegram |
| `weekly_harvest` | Sunday 10:00 | Push cooked meals to Notion |

---

## 2. Prerequisites

### Required Accounts & Tokens

| Service | What You Need | Where to Get It |
|---------|---------------|-----------------|
| **Telegram Bot** | `TELEGRAM_BOT_TOKEN` | DM `@BotFather` → `/newbot` |
| **Telegram Chat** | `TELEGRAM_CHAT_ID` | DM `@userinfobot` → copy ID |
| **Notion** | `NOTION_TOKEN` | https://www.notion.so/my-integrations → New Integration |
| **Notion DB** | `NOTION_DATABASE_ID` | Open your Recipes DB → URL contains 32-char ID |
| **GitHub** | Repo access | https://github.com/EricBell/meal-planner |

### Optional: PostgreSQL (Production)

If not using SQLite, provision a PostgreSQL database and get:
- `DATABASE_URL=postgresql://user:pass@host:5432/meal_planner`

---

## 3. Notion Database Setup

### Required: Recipes Database

Create a database in Notion with these properties:

| Property Name | Type | Required | Notes |
|---------------|------|----------|-------|
| **Name** | Title | ✅ | Recipe name |
| **Entree Type** | Select | ✅ | Options: beef, pork, chicken, haddock, salmon, shrimp, tofu, eggs, ground_beef, ground_turkey |
| **Prep Time (min)** | Number | | |
| **Cook Time (min)** | Number | | |
| **Servings** | Number | | Default: 4 |
| **Description** | Rich Text | | |
| **Source URL** | URL | | |
| **Tags** | Multi-select | | |
| **Status** | Select | | Options: Active, Archived |

### Page Content Structure (Auto-created by sync)

The sync populates each page with:
1. **Ingredients** — Bulleted list with quantities
2. **Instructions** — Numbered list

### Optional: Pantry Database

Separate database for inventory tracking (not yet fully implemented):
- Properties: Ingredient (Title), Quantity (Number), Unit (Select), Minimum Threshold (Number)

---

## 4. Telegram Bot Setup

### 1. Create Bot

```bash
# In Telegram, DM @BotFather:
/newbot
# Name: Family Meal Planner
# Username: yourname_mealplanner_bot
# → Copy the token (TELEGRAM_BOT_TOKEN)
```

### 2. Get Chat ID

```bash
# DM @userinfobot
# → Copy your numeric chat ID (TELEGRAM_CHAT_ID)
```

### 3. Test Bot

```bash
# In terminal (after deploy):
curl -X POST "https://api.telegram.org/bot<TOKEN>/getMe"
# Should return bot info
```

### 4. Bot Commands (Auto-registered)

| Command | Description |
|---------|-------------|
| `/start` | Welcome + help |
| `/today` | Today's meal plan with full recipe |
| `/week` | This week's meal plan overview |
| `/shopping` | Current shopping list |
| `/pantry` | Pantry inventory |
| `/add_pantry <item> <qty> <unit>` | Add to pantry |
| `/replace <YYYY-MM-DD>` | Replace a meal with alternatives |
| `/search <query>` | Search local + Notion recipes |
| `/harvest` | Sync cooked meals to Notion |
| `/help` | Show help |

---

## 5. Dokploy Deployment

### 1. Create New App in Dokploy

1. Open Dokploy dashboard
2. **New App** → **Docker Compose**
3. **Repository**: `https://github.com/EricBell/meal-planner`
4. **Branch**: `main` (or `master`)
5. **Docker Compose File**: `docker-compose.yml`
6. **Build Context**: `.` (root)

### 2. Configure Environment Variables

In Dokploy App → **Environment Variables**, add:

| Variable | Value | Required |
|----------|-------|----------|
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-DEF...` | ✅ |
| `TELEGRAM_CHAT_ID` | `123456789` | ✅ |
| `NOTION_TOKEN` | `secret_xxx` | ✅ |
| `NOTION_DATABASE_ID` | `32-char-id` | ✅ |
| `NOTION_PANTRY_DATABASE_ID` | `32-char-id` | Optional |
| `DATABASE_URL` | `sqlite:///./data/meal_planner.db` | Default |
| `MORNING_DELIVERY_HOUR` | `8` | Default |
| `MORNING_DELIVERY_MINUTE` | `0` | Default |
| `WEEKLY_HARVEST_DAY` | `sunday` | Default |
| `WEEKLY_HARVEST_HOUR` | `10` | Default |
| `DEFAULT_ENTREES` | `beef,pork,chicken,haddock,salmon,shrimp,tofu,eggs,ground_beef,ground_turkey` | Default |
| `DAYS_TO_PLAN` | `7` | Default |
| `LOG_LEVEL` | `INFO` | Default |

### 3. Configure Volumes

Dokploy auto-creates the volume from `docker-compose.yml`:
- **Volume**: `meal-planner-data` → `/app/data` (persists SQLite DB)

### 4. Deploy

1. Click **Deploy**
2. Wait for build + startup (~2-3 min first deploy)
3. Check **Logs** for:
   ```
   INFO:     Application startup complete.
   INFO     Starting Meal Planner API
   WARNING  Telegram credentials not set - bot disabled
   # ... or on success:
   INFO     Telegram bot and scheduler started
   ```

### 5. Verify Health

```bash
# In Dokploy terminal or via ingress:
curl https://your-app.dokploy.com/health
# {"status":"healthy","timestamp":"..."}
```

---

## 6. Post-Deploy Initialization

### 1. Seed Database (One-time)

```bash
# In Dokploy App → Terminal:
cd /app && python seed.py
# Output:
# 🌱 Seeding database...
# Adding staple ingredients...
#   Added 45 staples
# Adding recipes...
#   1. Classic Beef Stroganoff (beef)
#   ...
# ✅ Seeded 20 recipes and 45 staples
```

### 2. Generate First Week's Meal Plan

```bash
# Option A: Via API
curl -X POST "https://your-app.dokploy.com/meal-plans/generate?start_date=2026-10-03T00:00:00%2B00:00&days=7"

# Option B: Trigger scheduler job
curl -X POST https://your-app.dokploy.com/scheduler/trigger/weekly_meal_plan
```

### 3. Test Telegram Delivery

```bash
# Trigger morning delivery manually
curl -X POST https://your-app.dokploy.com/scheduler/trigger/morning_delivery

# Or use bot command in Telegram:
/today
```

### 4. Verify Notion Sync

```bash
# Push a recipe to Notion
curl -X POST https://your-app.dokploy.com/notion/push-recipe/1

# Harvest cooked meals
curl -X POST "https://your-app.dokploy.com/notion/harvest?days_back=30"
```

---

## 7. Daily Operations

### Morning Routine (Automated)

| Time | Action |
|------|--------|
| 00:05 | Scheduler generates tomorrow's meal plan |
| 08:00 | Telegram bot sends today's recipe to chat |

### User Actions (Via Telegram)

| Scenario | Action |
|----------|--------|
| Don't like today's meal | `/replace 2026-10-03` → pick alternative |
| Need to buy groceries | `/shopping` → review list → mark purchased |
| Check what's in pantry | `/pantry` |
| Add item to pantry | `/add_pantry chicken 2 kg` |
| Cooked the meal | Click ✅ Confirm in morning message, or `/today` → Confirm |
| Skip tonight | Click ⏭️ Skip in morning message |

### Weekly Routine (Automated)

| Time | Action |
|------|--------|
| Sunday 01:00 | Generate full week plan + shopping list |
| Sunday 10:00 | Harvest cooked meals → Notion |

### Manual Weekly Tasks

```bash
# Review shopping list for the week
/shopping

# Add any missing pantry staples
/add_pantry olive_oil 1 l

# Sync any cooked meals not yet harvested
/harvest
```

---

## 8. Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | **Required** Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | — | **Required** Numeric chat ID |
| `NOTION_TOKEN` | — | **Required** Notion integration token |
| `NOTION_DATABASE_ID` | — | **Required** Recipes database ID |
| `NOTION_PANTRY_DATABASE_ID` | — | Optional pantry database ID |
| `DATABASE_URL` | `sqlite:///./data/meal_planner.db` | SQLite (in volume) or PostgreSQL URL |
| `MORNING_DELIVERY_HOUR` | `8` | 24-hour format |
| `MORNING_DELIVERY_MINUTE` | `0` | |
| `WEEKLY_HARVEST_DAY` | `sunday` | Cron day name |
| `WEEKLY_HARVEST_HOUR` | `10` | 24-hour format |
| `DEFAULT_ENTREES` | `beef,pork,chicken,haddock,salmon,shrimp,tofu,eggs,ground_beef,ground_turkey` | Comma-separated |
| `DAYS_TO_PLAN` | `7` | Planning horizon |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR |

### Entree Types (Fixed)

```
beef, pork, chicken, haddock, salmon, shrimp, tofu, eggs, ground_beef, ground_turkey
```

To modify: Edit `DEFAULT_ENTREES` env var and `app/models/__init__.py` `EntreeType` enum.

### Staple Ingredients (Never on Shopping List)

```
salt, pepper, olive_oil, vegetable_oil, butter, garlic, onion, flour, sugar,
rice, pasta, soy_sauce, vinegar, + 30 more (see seed.py)
```

---

## 9. API Reference

### Base URL

```
https://your-app.dokploy.com
```

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/recipes` | List all recipes |
| `GET` | `/recipes/{id}` | Get recipe with ingredients |
| `POST` | `/recipes` | Create recipe |
| `GET` | `/meal-plans/today` | Today's meal plan |
| `GET` | `/meal-plans/week` | This week's plans |
| `POST` | `/meal-plans/generate` | Generate plan (query: start_date, days) |
| `POST` | `/meal-plans/{id}/replace` | Replace meal |
| `POST` | `/meal-plans/{id}/cook` | Mark cooked |
| `GET` | `/shopping` | Current shopping list |
| `POST` | `/shopping/generate` | Generate from meal plans |
| `POST` | `/shopping/clear` | Mark all purchased |
| `GET` | `/pantry` | Pantry inventory |
| `POST` | `/pantry` | Add/update pantry item |
| `POST` | `/notion/push-recipe/{id}` | Push recipe to Notion |
| `POST` | `/notion/harvest` | Harvest cooked meals |
| `POST` | `/scheduler/trigger/{job_id}` | Manually trigger job |
| `GET` | `/scheduler/jobs` | List scheduled jobs |

### Example: Generate Meal Plan

```bash
curl -X POST "https://your-app.dokploy.com/meal-plans/generate?start_date=2026-10-03T00:00:00%2B00:00&days=7"
```

### Example: Replace Meal

```bash
curl -X POST "https://your-app.dokploy.com/meal-plans/1/replace?new_recipe_id=5&reason=don't_like_beef"
```

---

## 10. Troubleshooting

### Bot Not Sending Messages

| Check | Command |
|-------|---------|
| Bot token valid | `curl "https://api.telegram.org/bot<TOKEN>/getMe"` |
| Chat ID correct | `curl "https://api.telegram.org/bot<TOKEN>/getUpdates"` |
| Bot not blocked | Open chat with bot, send `/start` |
| Logs show startup | Check Dokploy logs for "Telegram bot and scheduler started" |

### Scheduler Not Running

```bash
# Check jobs
curl https://your-app.dokploy.com/scheduler/jobs

# Manually trigger
curl -X POST https://your-app.dokploy.com/scheduler/trigger/weekly_meal_plan
```

### Notion Sync Failing

| Issue | Fix |
|-------|-----|
| 401 Unauthorized | Check `NOTION_TOKEN` — re-create integration |
| 404 Database not found | Check `NOTION_DATABASE_ID` — must be 32-char ID from URL |
| Properties missing | Ensure Notion DB has required properties (see Section 3) |
| Rate limited | Wait — Notion allows ~3 req/sec |

### Database Locked (SQLite)

```
sqlite3.OperationalError: database is locked
```

**Cause:** Multiple processes accessing DB (e.g., running seed.py while server runs)

**Fix:**
```bash
# Stop app in Dokploy, then:
cd /app && python seed.py
# Restart app
```

### Morning Delivery Not Arriving

1. Check scheduler logs: `curl /scheduler/jobs`
2. Verify `MORNING_DELIVERY_HOUR` timezone (server runs UTC)
3. Test manually: `curl -X POST /scheduler/trigger/morning_delivery`

---

## 11. Backup & Recovery

### SQLite Backup (Automatic via Volume)

Dokploy volume `meal-planner-data` persists `/app/data/meal_planner.db`.

```bash
# Manual backup (from Dokploy terminal):
cp /app/data/meal_planner.db /app/data/meal_planner.db.backup.$(date +%F)
```

### Full Backup (Git + DB)

```bash
# On VPS host (requires root for Docker volume):
docker run --rm -v hermes-hermes-waz1is_hermes-data:/data -v $(pwd):/backup alpine tar czf /backup/meal-planner-backup-$(date +%F).tar.gz /data
```

### Recovery

```bash
# Restore DB:
cp /app/data/meal_planner.db.backup.2026-10-03 /app/data/meal_planner.db
# Restart app
```

---

## 12. Updating the Application

### Via Dokploy (Standard)

1. Push changes to GitHub:
   ```bash
   git add . && git commit -m "Fix: ..." && git push
   ```
2. In Dokploy: Click **Deploy** → rebuilds from latest commit

### Database Migrations (Future)

When schema changes:
```bash
# In Dokploy terminal:
cd /app
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Zero-Downtime Deploy Notes

- SQLite doesn't support concurrent writes well
- For true zero-downtime: migrate to PostgreSQL
- Current: brief downtime during deploy (container restart)

---

## 13. Security Checklist

- [ ] `TELEGRAM_BOT_TOKEN` stored only in Dokploy env vars (not in repo)
- [ ] `NOTION_TOKEN` stored only in Dokploy env vars
- [ ] `.env` file in `.gitignore` (already done)
- [ ] Database file excluded from git (already done)
- [ ] HTTPS enforced by Dokploy ingress
- [ ] No exposed ports except Dokploy ingress
- [ ] Bot only responds to your `TELEGRAM_CHAT_ID` (single-user)

---

## 14. Monitoring & Alerts

### Health Check

```bash
# Add to cron or monitoring:
curl -f https://your-app.dokploy.com/health || alert
```

### Key Metrics to Watch

| Metric | Normal | Alert If |
|--------|--------|----------|
| `/health` response | 200 OK | ≠ 200 |
| Morning delivery sent | Daily 08:00 | Missing > 1 day |
| Weekly harvest | Sunday 10:00 | Missing |
| Shopping list generated | After weekly plan | Empty when meals exist |

### Log Patterns to Monitor

```bash
# Error patterns:
grep -i "error\|failed\|exception" /var/log/meal-planner.log

# Success patterns:
grep "morning delivery sent\|harvest complete" /var/log/meal-planner.log
```

---

## 15. Rollback Procedure

```bash
# 1. Find previous commit
git log --oneline -10

# 2. Tag current (bad) deploy
git tag rollback-bad-$(date +%F)

# 3. Reset to known good commit
git reset --hard <good-commit-sha>
git push --force

# 4. Redeploy in Dokploy
# Click Deploy
```

---

## 16. Useful Commands Reference

### Dokploy Terminal

```bash
# Seed DB
python seed.py

# Check DB contents
sqlite3 data/meal_planner.db "SELECT name, entree_type FROM recipe;"

# View shopping list
curl -s localhost:8000/shopping | jq .

# Trigger scheduler job
curl -X POST localhost:8000/scheduler/trigger/weekly_meal_plan

# View jobs
curl -s localhost:8000/scheduler/jobs | jq .

# Test Telegram
curl -X POST localhost:8000/scheduler/trigger/morning_delivery
```

### Local Development

```bash
# Clone
git clone https://github.com/EricBell/meal-planner
cd meal-planner

# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
# Edit .env with your tokens

# Seed & run
python seed.py
uvicorn app.main:app --reload
```

---

## 17. File Structure Reference

```
meal-planner/
├── app/
│   ├── main.py              # FastAPI app, endpoints, lifespan
│   ├── config.py            # Pydantic settings
│   ├── database.py          # SQLModel engine/session
│   ├── models/__init__.py   # DB models (Recipe, MealPlan, Pantry, etc.)
│   ├── services/
│   │   ├── recipe.py        # Recipe CRUD + meal planning logic
│   │   ├── pantry.py        # Inventory + shopping lists
│   │   └── notion.py        # Notion bi-directional sync
│   ├── bot/telegram_bot.py  # Telegram bot + commands
│   ├── scheduler/jobs.py    # APScheduler job definitions
│   └── schemas.py           # Pydantic request/response models
├── seed.py                  # Initial data (20 recipes, 45 staples)
├── docker-compose.yml       # Dokploy deployment
├── Dockerfile               # Container build
├── pyproject.toml           # Dependencies
├── .env.example             # Environment template
├── README.md                # Project documentation
├── s6/
│   ├── run                  # s6 service entrypoint
│   └── type                 # "longrun"
└── alembic/                 # DB migrations (future)
```

---

## 18. Support & Escalation

### Self-Service
1. Check Dokploy logs
2. Check this runbook troubleshooting section
3. Test via API endpoints directly

### Common Fixes
| Problem | Quick Fix |
|---------|-----------|
| Bot silent | Verify `TELEGRAM_CHAT_ID` matches your chat |
| No meals generated | Run `POST /meal-plans/generate` manually |
| Shopping list wrong | Check pantry staples in `/pantry` |
| Notion sync fails | Verify DB properties match Section 3 |

### When to Rebuild
- Dependency changes (`pyproject.toml`)
- Dockerfile changes
- Base image updates

---

## Appendix A: Quick Start Checklist

- [ ] GitHub repo cloned to Dokploy
- [ ] Environment variables set in Dokploy
- [ ] Notion database created with correct properties
- [ ] Telegram bot created, token + chat ID saved
- [ ] App deployed successfully
- [ ] `python seed.py` run in terminal
- [ ] First meal plan generated
- [ ] `/today` works in Telegram
- [ ] `/shopping` shows items
- [ ] `/harvest` pushes to Notion
- [ ] Morning delivery arrives at 08:00
- [ ] Weekly plan generates Sunday 01:00

---

*End of Runbook*