#!/usr/bin/env python3
"""
Seed script: Populate initial recipes, pantry staples, and entree types.
Run after first deployment: `python seed.py`
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app.database import init_db, get_session_sync
from app.services.recipe import RecipeService
from app.services.pantry import PantryService
from app.models import EntreeType, Unit, Ingredient

# Initialize DB
init_db()

# ===== STAPLE INGREDIENTS (always assumed available) =====
STAPLES = [
    ("salt", Unit.TSP, "seasoning"),
    ("black pepper", Unit.TSP, "seasoning"),
    ("olive oil", Unit.TBSP, "oil"),
    ("vegetable oil", Unit.TBSP, "oil"),
    ("butter", Unit.TBSP, "dairy"),
    ("garlic", Unit.CLoves, "aromatic"),
    ("onion", Unit.PIECES, "aromatic"),
    ("yellow onion", Unit.PIECES, "aromatic"),
    ("flour", Unit.CUPS, "pantry"),
    ("sugar", Unit.CUPS, "pantry"),
    ("brown sugar", Unit.CUPS, "pantry"),
    ("rice", Unit.CUPS, "grain"),
    ("pasta", Unit.OUNCES, "grain"),
    ("spaghetti", Unit.OUNCES, "grain"),
    ("penne", Unit.OUNCES, "grain"),
    ("soy sauce", Unit.TBSP, "condiment"),
    ("vinegar", Unit.TBSP, "condiment"),
    ("apple cider vinegar", Unit.TBSP, "condiment"),
    ("balsamic vinegar", Unit.TBSP, "condiment"),
    ("tomato paste", Unit.TBSP, "pantry"),
    ("canned tomatoes", Unit.OUNCES, "pantry"),
    ("chicken broth", Unit.CUPS, "pantry"),
    ("beef broth", Unit.CUPS, "pantry"),
    ("vegetable broth", Unit.CUPS, "pantry"),
    ("eggs", Unit.PIECES, "protein"),
    ("milk", Unit.CUPS, "dairy"),
    ("heavy cream", Unit.CUPS, "dairy"),
    ("parmesan cheese", Unit.CUPS, "dairy"),
    ("cheddar cheese", Unit.CUPS, "dairy"),
    ("mozzarella cheese", Unit.CUPS, "dairy"),
    ("breadcrumbs", Unit.CUPS, "pantry"),
    ("panko", Unit.CUPS, "pantry"),
    ("dried oregano", Unit.TSP, "spice"),
    ("dried basil", Unit.TSP, "spice"),
    ("dried thyme", Unit.TSP, "spice"),
    ("paprika", Unit.TSP, "spice"),
    ("cumin", Unit.TSP, "spice"),
    ("chili powder", Unit.TSP, "spice"),
    ("bay leaves", Unit.PIECES, "spice"),
    ("honey", Unit.TBSP, "pantry"),
    ("mustard", Unit.TBSP, "condiment"),
    ("worcestershire sauce", Unit.TSP, "condiment"),
    ("hot sauce", Unit.TSP, "condiment"),
    ("lemon", Unit.PIECES, "produce"),
    ("lime", Unit.PIECES, "produce"),
]

# ===== INITIAL RECIPES =====
RECIPES = [
    # BEEF
    {
        "name": "Classic Beef Stroganoff",
        "entree_type": EntreeType.BEEF,
        "description": "Tender beef in rich mushroom sour cream sauce over egg noodles",
        "instructions": "1. Slice beef against grain into thin strips. Season with salt, pepper, paprika.\n2. Sear beef in batches in hot oil until browned. Remove.\n3. In same pan, sauté onions and mushrooms until golden.\n4. Add garlic, cook 30s. Stir in tomato paste, cook 1 min.\n5. Deglaze with broth, scrape up fond. Simmer 5 min.\n6. Reduce heat, stir in sour cream and mustard. Don't boil.\n7. Return beef, heat through. Serve over egg noodles.",
        "prep_time_minutes": 15,
        "cook_time_minutes": 25,
        "servings": 4,
        "ingredients": [
            {"name": "beef sirloin", "quantity": 1.5, "unit": Unit.POUNDS},
            {"name": "mushrooms", "quantity": 8, "unit": Unit.OUNCES},
            {"name": "onion", "quantity": 1, "unit": Unit.PIECES},
            {"name": "garlic", "quantity": 3, "unit": Unit.CLoves},
            {"name": "beef broth", "quantity": 1, "unit": Unit.CUPS},
            {"name": "sour cream", "quantity": 1, "unit": Unit.CUPS},
            {"name": "tomato paste", "quantity": 1, "unit": Unit.TBSP},
            {"name": "mustard", "quantity": 1, "unit": Unit.TBSP},
            {"name": "paprika", "quantity": 1, "unit": Unit.TSP},
            {"name": "egg noodles", "quantity": 12, "unit": Unit.OUNCES},
        ],
        "tags": ["comfort", "weeknight", "mushroom"],
    },
    {
        "name": "Korean Beef Bulgogi",
        "entree_type": EntreeType.BEEF,
        "description": "Sweet-savory marinated beef, quick-cooked with vegetables",
        "instructions": "1. Slice beef very thin against grain. Marinate 30+ min in soy sauce, sugar, sesame oil, garlic, ginger, pear/apple puree.\n2. Heat pan/wok very hot. Cook beef in batches 1-2 min until caramelized.\n3. Add sliced onions, carrots, scallions. Cook 2-3 min.\n4. Garnish with sesame seeds. Serve with rice and lettuce wraps.",
        "prep_time_minutes": 20,
        "cook_time_minutes": 10,
        "servings": 4,
        "ingredients": [
            {"name": "beef ribeye", "quantity": 1.5, "unit": Unit.POUNDS},
            {"name": "soy sauce", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "brown sugar", "quantity": 0.25, "unit": Unit.CUPS},
            {"name": "sesame oil", "quantity": 2, "unit": Unit.TBSP},
            {"name": "garlic", "quantity": 4, "unit": Unit.CLoves},
            {"name": "ginger", "quantity": 1, "unit": Unit.TBSP},
            {"name": "asian pear", "quantity": 0.5, "unit": Unit.PIECES},
            {"name": "onion", "quantity": 1, "unit": Unit.PIECES},
            {"name": "carrot", "quantity": 1, "unit": Unit.PIECES},
            {"name": "scallions", "quantity": 3, "unit": Unit.PIECES},
            {"name": "sesame seeds", "quantity": 1, "unit": Unit.TBSP},
        ],
        "tags": ["korean", "quick", "marinated"],
    },

    # PORK
    {
        "name": "Pork Carnitas",
        "entree_type": EntreeType.PORK,
        "description": "Crispy Mexican pulled pork - perfect for tacos, bowls, nachos",
        "instructions": "1. Cut pork shoulder into 2-inch chunks. Season generously with salt, pepper, cumin, oregano.\n2. Place in Dutch oven with orange juice, lime juice, garlic, bay leaves. Add water to barely cover.\n3. Simmer uncovered 2.5-3 hours until tender and liquid evaporates.\n4. Shred pork. Increase heat, fry in rendered fat until edges crisp.\n5. Serve in tortillas with onion, cilantro, salsa.",
        "prep_time_minutes": 20,
        "cook_time_minutes": 180,
        "servings": 6,
        "ingredients": [
            {"name": "pork shoulder", "quantity": 3, "unit": Unit.POUNDS},
            {"name": "orange", "quantity": 1, "unit": Unit.PIECES},
            {"name": "lime", "quantity": 2, "unit": Unit.PIECES},
            {"name": "garlic", "quantity": 6, "unit": Unit.CLoves},
            {"name": "cumin", "quantity": 1, "unit": Unit.TBSP},
            {"name": "oregano", "quantity": 1, "unit": Unit.TBSP},
            {"name": "bay leaves", "quantity": 3, "unit": Unit.PIECES},
            {"name": "corn tortillas", "quantity": 12, "unit": Unit.PIECES},
        ],
        "tags": ["mexican", "meal-prep", "tacos", "slow-cooked"],
    },
    {
        "name": "Pork Chops with Apple Cider Pan Sauce",
        "entree_type": EntreeType.PORK,
        "description": "Pan-seared chops with sweet-tangy apple cider reduction",
        "instructions": "1. Brine chops 30 min in salt water (optional). Pat dry, season.\n2. Sear chops 4-5 min/side until 140°F. Remove.\n3. In pan, sauté apples in butter until golden. Remove.\n4. Deglaze with apple cider vinegar and broth. Reduce by half.\n5. Stir in mustard, cream, thyme. Return chops and apples to warm.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 20,
        "servings": 4,
        "ingredients": [
            {"name": "pork chops", "quantity": 4, "unit": Unit.PIECES},
            {"name": "apple", "quantity": 1, "unit": Unit.PIECES},
            {"name": "apple cider vinegar", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "chicken broth", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "mustard", "quantity": 1, "unit": Unit.TBSP},
            {"name": "heavy cream", "quantity": 0.25, "unit": Unit.CUPS},
            {"name": "thyme", "quantity": 1, "unit": Unit.TSP},
        ],
        "tags": ["quick", "pan-sauce", "fall"],
    },

    # CHICKEN
    {
        "name": "Chicken Piccata",
        "entree_type": EntreeType.CHICKEN,
        "description": "Classic Italian - lemon caper butter sauce over pounded cutlets",
        "instructions": "1. Pound chicken breasts to 1/2 inch thickness. Season, dredge in flour.\n2. Pan-fry in oil/butter 3-4 min/side until golden. Remove.\n3. Deglaze pan with wine, broth, lemon juice, capers. Reduce.\n4. Whisk in cold butter pieces. Return chicken to coat.\n5. Garnish with parsley. Serve with pasta or potatoes.",
        "prep_time_minutes": 15,
        "cook_time_minutes": 15,
        "servings": 4,
        "ingredients": [
            {"name": "chicken breast", "quantity": 2, "unit": Unit.POUNDS},
            {"name": "flour", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "white wine", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "chicken broth", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "lemon", "quantity": 1, "unit": Unit.PIECES},
            {"name": "capers", "quantity": 3, "unit": Unit.TBSP},
            {"name": "butter", "quantity": 4, "unit": Unit.TBSP},
            {"name": "parsley", "quantity": 2, "unit": Unit.TBSP},
        ],
        "tags": ["italian", "quick", "lemon", "caper"],
    },
    {
        "name": "Chicken Tikka Masala",
        "entree_type": EntreeType.CHICKEN,
        "description": "Grilled marinated chicken in creamy spiced tomato sauce",
        "instructions": "1. Marinate chicken in yogurt, garlic, ginger, garam masala, turmeric, chili powder 2+ hours.\n2. Grill or broil chicken until charred. Cut into pieces.\n3. Sauté onions, garlic, ginger. Add spices, cook 1 min.\n4. Add tomato puree, simmer 10 min. Blend smooth (optional).\n5. Stir in cream, chicken. Simmer 5 min. Garnish with cilantro.",
        "prep_time_minutes": 20,
        "cook_time_minutes": 30,
        "servings": 4,
        "ingredients": [
            {"name": "chicken thigh", "quantity": 2, "unit": Unit.POUNDS},
            {"name": "yogurt", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "garam masala", "quantity": 2, "unit": Unit.TSP},
            {"name": "turmeric", "quantity": 1, "unit": Unit.TSP},
            {"name": "chili powder", "quantity": 1, "unit": Unit.TSP},
            {"name": "tomato puree", "quantity": 1, "unit": Unit.CUPS},
            {"name": "heavy cream", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "onion", "quantity": 1, "unit": Unit.PIECES},
            {"name": "garlic", "quantity": 4, "unit": Unit.CLoves},
            {"name": "ginger", "quantity": 1, "unit": Unit.TBSP},
        ],
        "tags": ["indian", "curry", "spicy", "make-ahead"],
    },

    # HADDOCK
    {
        "name": "Baked Haddock with Herb Crumb Topping",
        "entree_type": EntreeType.HADDOCK,
        "description": "Flaky white fish with crispy panko-herb crust",
        "instructions": "1. Pat fish dry. Place in greased baking dish.\n2. Mix panko, melted butter, parsley, dill, lemon zest, garlic.\n3. Press mixture onto fish fillets.\n4. Bake 400°F 12-15 min until fish flakes and topping golden.\n5. Serve with lemon wedges and tartar sauce.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "servings": 4,
        "ingredients": [
            {"name": "haddock fillets", "quantity": 1.5, "unit": Unit.POUNDS},
            {"name": "panko", "quantity": 1, "unit": Unit.CUPS},
            {"name": "butter", "quantity": 3, "unit": Unit.TBSP},
            {"name": "parsley", "quantity": 2, "unit": Unit.TBSP},
            {"name": "dill", "quantity": 1, "unit": Unit.TBSP},
            {"name": "lemon", "quantity": 1, "unit": Unit.PIECES},
            {"name": "garlic", "quantity": 2, "unit": Unit.CLoves},
        ],
        "tags": ["quick", "baked", "healthy", "seafood"],
    },
    {
        "name": "Fish and Chips (Haddock)",
        "entree_type": EntreeType.HADDOCK,
        "description": "Beer-battered crispy fish with thick-cut fries",
        "instructions": "1. Cut potatoes into thick fries. Soak 30 min, dry thoroughly.\n2. Fry potatoes at 325°F 5 min. Drain.\n3. Make batter: flour, baking powder, beer, salt. Rest 15 min.\n4. Dip fish in batter, fry at 375°F 4-5 min until golden.\n5. Re-fry potatoes at 375°F 2-3 min until crisp.\n6. Serve with malt vinegar and tartar sauce.",
        "prep_time_minutes": 30,
        "cook_time_minutes": 20,
        "servings": 4,
        "ingredients": [
            {"name": "haddock fillets", "quantity": 1.5, "unit": Unit.POUNDS},
            {"name": "russet potatoes", "quantity": 2, "unit": Unit.POUNDS},
            {"name": "flour", "quantity": 1.5, "unit": Unit.CUPS},
            {"name": "baking powder", "quantity": 1, "unit": Unit.TSP},
            {"name": "beer", "quantity": 1, "unit": Unit.CUPS},
            {"name": "malt vinegar", "quantity": 0.25, "unit": Unit.CUPS},
        ],
        "tags": ["british", "fried", "comfort", "weekend"],
    },

    # SALMON
    {
        "name": "Miso-Glazed Salmon",
        "entree_type": EntreeType.SALMON,
        "description": "Sweet-savory Japanese glaze, broiled until caramelized",
        "instructions": "1. Mix white miso, mirin, sake, sugar into paste.\n2. Pat salmon dry. Brush generously with glaze.\n3. Marinate 30 min (or overnight).\n4. Broil 6-8 min until caramelized and cooked through.\n5. Garnish with scallions and sesame seeds. Serve with rice.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 10,
        "servings": 4,
        "ingredients": [
            {"name": "salmon fillets", "quantity": 1.5, "unit": Unit.POUNDS},
            {"name": "white miso paste", "quantity": 3, "unit": Unit.TBSP},
            {"name": "mirin", "quantity": 2, "unit": Unit.TBSP},
            {"name": "sake", "quantity": 2, "unit": Unit.TBSP},
            {"name": "sugar", "quantity": 1, "unit": Unit.TBSP},
            {"name": "scallions", "quantity": 2, "unit": Unit.PIECES},
            {"name": "sesame seeds", "quantity": 1, "unit": Unit.TSP},
        ],
        "tags": ["japanese", "quick", "glazed", "healthy"],
    },
    {
        "name": "Salmon en Papillote",
        "entree_type": EntreeType.SALMON,
        "description": "Steamed in parchment with vegetables - no cleanup",
        "instructions": "1. Cut parchment into large hearts. Place salmon on one half.\n2. Top with sliced zucchini, bell pepper, cherry tomatoes, herbs.\n3. Drizzle with olive oil, white wine, lemon. Season.\n4. Fold parchment, crimp edges to seal.\n5. Bake 400°F 12-15 min. Puff up and serve at table.",
        "prep_time_minutes": 15,
        "cook_time_minutes": 15,
        "servings": 4,
        "ingredients": [
            {"name": "salmon fillets", "quantity": 4, "unit": Unit.PIECES},
            {"name": "zucchini", "quantity": 1, "unit": Unit.PIECES},
            {"name": "bell pepper", "quantity": 1, "unit": Unit.PIECES},
            {"name": "cherry tomatoes", "quantity": 1, "unit": Unit.CUPS},
            {"name": "white wine", "quantity": 0.25, "unit": Unit.CUPS},
            {"name": "lemon", "quantity": 1, "unit": Unit.PIECES},
            {"name": "thyme", "quantity": 1, "unit": Unit.TSP},
        ],
        "tags": ["healthy", "no-cleanup", "steamed", "elegant"],
    },

    # SHRIMP
    {
        "name": "Shrimp Scampi",
        "entree_type": EntreeType.SHRIMP,
        "description": "Garlic butter shrimp over linguine - restaurant classic",
        "instructions": "1. Cook linguine al dente. Reserve pasta water.\n2. Sauté shrimp in butter/oil 1-2 min/side until pink. Remove.\n3. In same pan, sauté garlic, red pepper flakes 30s.\n4. Add wine, lemon juice, reduce. Stir in butter, parsley.\n5. Toss shrimp and pasta in sauce. Add pasta water to emulsify.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "servings": 4,
        "ingredients": [
            {"name": "shrimp", "quantity": 1.5, "unit": Unit.POUNDS},
            {"name": "linguine", "quantity": 12, "unit": Unit.OUNCES},
            {"name": "garlic", "quantity": 4, "unit": Unit.CLoves},
            {"name": "white wine", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "lemon", "quantity": 1, "unit": Unit.PIECES},
            {"name": "butter", "quantity": 4, "unit": Unit.TBSP},
            {"name": "red pepper flakes", "quantity": 0.25, "unit": Unit.TSP},
            {"name": "parsley", "quantity": 2, "unit": Unit.TBSP},
        ],
        "tags": ["italian", "quick", "pasta", "garlic"],
    },
    {
        "name": "Coconut Curry Shrimp",
        "entree_type": EntreeType.SHRIMP,
        "description": "Thai-style coconut curry with shrimp and vegetables",
        "instructions": "1. Sauté curry paste in coconut cream until fragrant.\n2. Add remaining coconut milk, fish sauce, sugar, lime leaves. Simmer 5 min.\n3. Add vegetables (bell pepper, bamboo shoots). Cook 3 min.\n4. Add shrimp, cook 2-3 min until pink.\n5. Finish with lime juice, basil. Serve over jasmine rice.",
        "prep_time_minutes": 15,
        "cook_time_minutes": 15,
        "servings": 4,
        "ingredients": [
            {"name": "shrimp", "quantity": 1.5, "unit": Unit.POUNDS},
            {"name": "red curry paste", "quantity": 2, "unit": Unit.TBSP},
            {"name": "coconut milk", "quantity": 2, "unit": Unit.CUPS},
            {"name": "fish sauce", "quantity": 1, "unit": Unit.TBSP},
            {"name": "brown sugar", "quantity": 1, "unit": Unit.TBSP},
            {"name": "bell pepper", "quantity": 1, "unit": Unit.PIECES},
            {"name": "lime", "quantity": 1, "unit": Unit.PIECES},
            {"name": "thai basil", "quantity": 0.25, "unit": Unit.CUPS},
        ],
        "tags": ["thai", "curry", "coconut", "quick"],
    },

    # TOFU
    {
        "name": "Mapo Tofu",
        "entree_type": EntreeType.TOFU,
        "description": "Sichuan classic - silky tofu in spicy fermented bean sauce",
        "instructions": "1. Blanch tofu cubes in salted water 1 min. Drain.\n2. Brown ground pork (or mushroom for veg) with doubanjiang.\n3. Add garlic, ginger, chili oil. Add broth, soy sauce.\n4. Gently fold in tofu. Simmer 3 min.\n5. Thicken with cornstarch slurry. Top with Sichuan peppercorn, scallions.",
        "prep_time_minutes": 15,
        "cook_time_minutes": 15,
        "servings": 4,
        "ingredients": [
            {"name": "soft tofu", "quantity": 14, "unit": Unit.OUNCES},
            {"name": "ground pork", "quantity": 0.5, "unit": Unit.POUNDS, "is_optional": True},
            {"name": "doubanjiang", "quantity": 2, "unit": Unit.TBSP},
            {"name": "fermented black beans", "quantity": 1, "unit": Unit.TBSP},
            {"name": "garlic", "quantity": 3, "unit": Unit.CLoves},
            {"name": "ginger", "quantity": 1, "unit": Unit.TBSP},
            {"name": "chicken broth", "quantity": 1, "unit": Unit.CUPS},
            {"name": "soy sauce", "quantity": 1, "unit": Unit.TBSP},
            {"name": "cornstarch", "quantity": 1, "unit": Unit.TBSP},
            {"name": "sichuan peppercorn", "quantity": 1, "unit": Unit.TSP},
        ],
        "tags": ["sichuan", "spicy", "vegetarian-option", "quick"],
    },
    {
        "name": "Crispy Tofu Stir-Fry",
        "entree_type": EntreeType.TOFU,
        "description": "Cornstarch-coated tofu with colorful vegetables in savory sauce",
        "instructions": "1. Press tofu 15 min. Cube, toss in cornstarch.\n2. Pan-fry tofu until all sides golden. Remove.\n3. Stir-fry vegetables: broccoli, bell pepper, carrot, snap peas.\n4. Add garlic, ginger. Return tofu.\n5. Sauce: soy sauce, rice vinegar, sesame oil, honey, cornstarch slurry.\n6. Toss everything. Garnish with cashews, scallions.",
        "prep_time_minutes": 20,
        "cook_time_minutes": 15,
        "servings": 4,
        "ingredients": [
            {"name": "firm tofu", "quantity": 14, "unit": Unit.OUNCES},
            {"name": "cornstarch", "quantity": 0.25, "unit": Unit.CUPS},
            {"name": "broccoli", "quantity": 2, "unit": Unit.CUPS},
            {"name": "bell pepper", "quantity": 1, "unit": Unit.PIECES},
            {"name": "carrot", "quantity": 1, "unit": Unit.PIECES},
            {"name": "snap peas", "quantity": 1, "unit": Unit.CUPS},
            {"name": "soy sauce", "quantity": 3, "unit": Unit.TBSP},
            {"name": "rice vinegar", "quantity": 1, "unit": Unit.TBSP},
            {"name": "sesame oil", "quantity": 1, "unit": Unit.TBSP},
            {"name": "honey", "quantity": 1, "unit": Unit.TBSP},
        ],
        "tags": ["vegetarian", "stir-fry", "crispy", "healthy"],
    },

    # EGGS
    {
        "name": "Shakshuka",
        "entree_type": EntreeType.EGGS,
        "description": "Eggs poached in spiced tomato sauce - breakfast for dinner",
        "instructions": "1. Sauté onion, bell pepper until soft. Add garlic, cumin, paprika, harissa.\n2. Add crushed tomatoes. Simmer 10 min until thickened.\n3. Make wells in sauce. Crack eggs into wells.\n4. Cover and cook 5-8 min until whites set, yolks runny.\n5. Top with feta, cilantro. Serve with crusty bread.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 20,
        "servings": 4,
        "ingredients": [
            {"name": "eggs", "quantity": 6, "unit": Unit.PIECES},
            {"name": "canned tomatoes", "quantity": 28, "unit": Unit.OUNCES},
            {"name": "onion", "quantity": 1, "unit": Unit.PIECES},
            {"name": "bell pepper", "quantity": 1, "unit": Unit.PIECES},
            {"name": "garlic", "quantity": 3, "unit": Unit.CLoves},
            {"name": "cumin", "quantity": 1, "unit": Unit.TSP},
            {"name": "paprika", "quantity": 1, "unit": Unit.TSP},
            {"name": "harissa", "quantity": 1, "unit": Unit.TBSP, "is_optional": True},
            {"name": "feta", "quantity": 4, "unit": Unit.OUNCES},
            {"name": "cilantro", "quantity": 0.25, "unit": Unit.CUPS},
        ],
        "tags": ["middle-eastern", "breakfast-for-dinner", "vegetarian", "one-pan"],
    },
    {
        "name": "Spanish Tortilla",
        "entree_type": EntreeType.EGGS,
        "description": "Classic potato onion omelette - serve hot or room temp",
        "instructions": "1. Thinly slice potatoes and onion. Cook slowly in olive oil 20 min until tender.\n2. Drain excess oil. Mix with beaten eggs, salt. Rest 10 min.\n3. Pour into non-stick pan. Cook low 5 min until edges set.\n4. Flip onto plate, slide back. Cook 3-4 min more.\n5. Cool 10 min before slicing.",
        "prep_time_minutes": 15,
        "cook_time_minutes": 30,
        "servings": 4,
        "ingredients": [
            {"name": "potatoes", "quantity": 2, "unit": Unit.POUNDS},
            {"name": "onion", "quantity": 1, "unit": Unit.PIECES},
            {"name": "eggs", "quantity": 6, "unit": Unit.PIECES},
            {"name": "olive oil", "quantity": 1, "unit": Unit.CUPS},
        ],
        "tags": ["spanish", "vegetarian", "make-ahead", "potato"],
    },

    # GROUND BEEF
    {
        "name": "Classic Bolognese",
        "entree_type": EntreeType.GROUND_BEEF,
        "description": "Slow-simmered meat sauce - the real deal, no shortcuts",
        "instructions": "1. Sauté pancetta, then onion, carrot, celery until soft.\n2. Add ground beef, brown well. Add wine, reduce.\n3. Add tomato paste, cook 2 min. Add milk, simmer 10 min.\n4. Add tomatoes, broth. Simmer uncovered 2-3 hours.\n5. Finish with nutmeg. Toss with tagliatelle, parmesan.",
        "prep_time_minutes": 20,
        "cook_time_minutes": 180,
        "servings": 6,
        "ingredients": [
            {"name": "ground beef", "quantity": 1, "unit": Unit.POUNDS},
            {"name": "pancetta", "quantity": 4, "unit": Unit.OUNCES},
            {"name": "onion", "quantity": 1, "unit": Unit.PIECES},
            {"name": "carrot", "quantity": 1, "unit": Unit.PIECES},
            {"name": "celery", "quantity": 2, "unit": Unit.PIECES},
            {"name": "red wine", "quantity": 1, "unit": Unit.CUPS},
            {"name": "milk", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "tomato paste", "quantity": 2, "unit": Unit.TBSP},
            {"name": "canned tomatoes", "quantity": 28, "unit": Unit.OUNCES},
            {"name": "beef broth", "quantity": 1, "unit": Unit.CUPS},
            {"name": "nutmeg", "quantity": 0.25, "unit": Unit.TSP},
            {"name": "tagliatelle", "quantity": 1, "unit": Unit.POUNDS},
        ],
        "tags": ["italian", "slow-cooked", "pasta", "meal-prep", "freezer-friendly"],
    },
    {
        "name": "Korean Beef Bowls (Bulgogi-style Ground Beef)",
        "entree_type": EntreeType.GROUND_BEEF,
        "description": "Weeknight version of bulgogi using ground beef - 15 minutes",
        "instructions": "1. Brown ground beef with garlic, ginger. Drain excess fat.\n2. Add soy sauce, brown sugar, sesame oil, gochujang, rice vinegar.\n3. Simmer 3 min until glazed. Stir in scallions.\n4. Serve over rice with fried egg, kimchi, cucumber.",
        "prep_time_minutes": 5,
        "cook_time_minutes": 10,
        "servings": 4,
        "ingredients": [
            {"name": "ground beef", "quantity": 1, "unit": Unit.POUNDS},
            {"name": "garlic", "quantity": 3, "unit": Unit.CLoves},
            {"name": "ginger", "quantity": 1, "unit": Unit.TBSP},
            {"name": "soy sauce", "quantity": 3, "unit": Unit.TBSP},
            {"name": "brown sugar", "quantity": 1, "unit": Unit.TBSP},
            {"name": "sesame oil", "quantity": 1, "unit": Unit.TBSP},
            {"name": "gochujang", "quantity": 1, "unit": Unit.TBSP, "is_optional": True},
            {"name": "rice vinegar", "quantity": 1, "unit": Unit.TSP},
            {"name": "scallions", "quantity": 3, "unit": Unit.PIECES},
            {"name": "sesame seeds", "quantity": 1, "unit": Unit.TSP},
        ],
        "tags": ["korean", "quick", "weeknight", "rice-bowl"],
    },

    # GROUND TURKEY
    {
        "name": "Turkey Chili",
        "entree_type": EntreeType.GROUND_TURKEY,
        "description": "Lean, hearty chili - freezes beautifully",
        "instructions": "1. Brown turkey with onion, garlic. Add spices, cook 1 min.\n2. Add tomatoes, beans, broth. Simmer 45 min.\n3. Adjust seasoning. Serve with toppings: cheese, sour cream, cilantro.",
        "prep_time_minutes": 15,
        "cook_time_minutes": 45,
        "servings": 6,
        "ingredients": [
            {"name": "ground turkey", "quantity": 1.5, "unit": Unit.POUNDS},
            {"name": "onion", "quantity": 1, "unit": Unit.PIECES},
            {"name": "garlic", "quantity": 4, "unit": Unit.CLoves},
            {"name": "chili powder", "quantity": 2, "unit": Unit.TBSP},
            {"name": "cumin", "quantity": 1, "unit": Unit.TBSP},
            {"name": "oregano", "quantity": 1, "unit": Unit.TSP},
            {"name": "canned tomatoes", "quantity": 28, "unit": Unit.OUNCES},
            {"name": "kidney beans", "quantity": 2, "unit": Unit.CANS},
            {"name": "black beans", "quantity": 1, "unit": Unit.CANS},
            {"name": "chicken broth", "quantity": 1, "unit": Unit.CUPS},
        ],
        "tags": ["mexican", "freezer-friendly", "meal-prep", "healthy", "lean"],
    },
    {
        "name": "Turkey Meatballs in Marinara",
        "entree_type": EntreeType.GROUND_TURKEY,
        "description": "Light, tender meatballs simmered in tomato sauce",
        "instructions": "1. Mix turkey, breadcrumbs, egg, parmesan, garlic, herbs. Form balls.\n2. Bake 400°F 15 min or pan-fry until browned.\n3. Simmer marinara 15 min. Add meatballs, cook 10 min.\n4. Serve over spaghetti or in hoagie rolls.",
        "prep_time_minutes": 20,
        "cook_time_minutes": 25,
        "servings": 4,
        "ingredients": [
            {"name": "ground turkey", "quantity": 1, "unit": Unit.POUNDS},
            {"name": "breadcrumbs", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "egg", "quantity": 1, "unit": Unit.PIECES},
            {"name": "parmesan", "quantity": 0.5, "unit": Unit.CUPS},
            {"name": "garlic", "quantity": 3, "unit": Unit.CLoves},
            {"name": "parsley", "quantity": 0.25, "unit": Unit.CUPS},
            {"name": "marinara", "quantity": 24, "unit": Unit.OUNCES},
            {"name": "spaghetti", "quantity": 12, "unit": Unit.OUNCES},
        ],
        "tags": ["italian", "pasta", "freezer-friendly", "meal-prep"],
    },
]


def main():
    print("🌱 Seeding database...")

    # Use a single session for all operations
    from app.database import get_session_sync
    session = get_session_sync()
    
    try:
        pantry_svc = PantryService(session)
        print("Adding staple ingredients...")
        for name, unit, category in STAPLES:
            ing = pantry_svc.get_or_create_ingredient(name, is_staple=True, default_unit=unit, category=category)
            # Set a default high quantity so they never appear on shopping list
            pantry_svc.set_pantry_quantity(name, 100, unit, minimum_threshold=0)
        print(f"  Added {len(STAPLES)} staples")

        recipe_svc = RecipeService(session)
        print("Adding recipes...")
        for i, recipe_data in enumerate(RECIPES):
            ingredients = recipe_data.pop("ingredients")
            tags = recipe_data.pop("tags", [])
            recipe = recipe_svc.create_recipe(ingredients=ingredients, tags=tags, **recipe_data)
            print(f"  {i+1}. {recipe.name} ({recipe.entree_type.value})")

        session.commit()
        print(f"\n✅ Seeded {len(RECIPES)} recipes and {len(STAPLES)} staples")
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()