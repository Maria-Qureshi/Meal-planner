"""
preprocess.py
-------------
Cleans and normalizes ingredient text so that matching/training works
consistently. Real-world datasets store ingredients as full phrases with
quantities and prep instructions baked in, e.g.:
    "1 1/2 cups plus 1 tablespoon lightly packed basil leaves, torn"
Simple word-stripping isn't reliable on text like that, so instead we match
against a curated list of common ingredient names and pull out whichever
one actually appears in the phrase.
"""

import re
import pandas as pd

KNOWN_INGREDIENTS = [
    "chicken breast", "chicken thigh", "chicken", "turkey", "duck",
    "ground beef", "beef", "steak", "pork", "bacon", "sausage", "ham",
    "shrimp", "salmon", "tuna", "cod", "fish", "tofu", "tempeh", "egg",
    "lamb",
    "parmesan", "mozzarella", "cheddar", "feta", "ricotta", "cream cheese",
    "cheese", "butter", "milk", "cream", "yogurt", "sour cream",
    "tomato", "onion", "garlic", "ginger", "carrot", "celery", "potato",
    "sweet potato", "bell pepper", "chili pepper", "jalapeno", "broccoli",
    "cauliflower", "spinach", "kale", "lettuce", "cabbage", "cucumber",
    "zucchini", "eggplant", "mushroom", "corn", "peas", "green bean",
    "asparagus", "avocado", "lemon", "lime", "orange", "apple", "banana",
    "basil", "cilantro", "parsley", "mint", "rosemary", "thyme", "oregano",
    "dill", "scallion", "leek", "shallot",
    "rice", "pasta", "noodle", "flour", "bread", "tortilla", "pizza dough",
    "quinoa", "oat", "lentil", "chickpea", "kidney bean", "black bean",
    "bean", "sugar", "brown sugar", "honey", "maple syrup", "vanilla",
    "cinnamon", "cumin", "paprika", "chili powder", "curry powder",
    "black pepper", "salt", "baking powder", "baking soda", "yeast",
    "cornstarch", "breadcrumb", "panko",
    "olive oil", "vegetable oil", "sesame oil", "soy sauce", "vinegar",
    "balsamic vinegar", "white wine", "red wine", "chicken broth",
    "vegetable broth", "beef broth", "stock", "coconut milk", "tomato sauce",
    "tomato paste", "ketchup", "mustard", "mayonnaise", "hot sauce",
    "worcestershire sauce", "fish sauce", "oyster sauce", "hoisin sauce",
    "almond", "walnut", "pecan", "cashew", "peanut", "peanut butter",
    "pine nut", "sesame seed", "chocolate", "cocoa", "coconut",
    "paneer",
]
KNOWN_INGREDIENTS = sorted(set(KNOWN_INGREDIENTS), key=len, reverse=True)

def clean_ingredient(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for ingredient in KNOWN_INGREDIENTS:
        if ingredient in text:
            return ingredient
    return None

def parse_ingredient_list(raw) -> list[str]:
    if not isinstance(raw, str) or not raw.strip():
        return []
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        import ast
        try:
            parts = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            parts = raw.strip("[]").split(",")
    else:
        parts = raw.split(",")
    cleaned = [clean_ingredient(str(p)) for p in parts]
    seen = set()
    result = []
    for c in cleaned:
        if c and c not in seen:
            seen.add(c)
            result.append(c)
    return result

def load_recipes(csv_path: str, ingredients_col: str = "ingredients",
                  title_col: str = "title", image_col: str = None,
                  image_folder: str = None, instructions_col: str = None) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["ingredients_clean"] = df[ingredients_col].apply(parse_ingredient_list)

    if title_col != "title":
        df["title"] = df[title_col]

    if image_col and image_col in df.columns and image_folder:
        df["image_path"] = df[image_col].apply(
            lambda name: f"{image_folder}/{name}.jpg" if pd.notna(name) else None
        )
    else:
        df["image_path"] = None

    if instructions_col and instructions_col in df.columns:
        df["instructions"] = df[instructions_col]
    else:
        df["instructions"] = None

    return df

if __name__ == "__main__":
    df = load_recipes("data/sample_recipes.csv")
    print(df[["title", "ingredients_clean"]].head())