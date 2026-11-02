"""
ingredient_parser.py
--------------------
Parses "2¾ tsp. kosher salt, divided" into:
    {item, quantity, unit, notes, category}
"""

import re
import ast
from preprocess import clean_ingredient

UNICODE_FRACTIONS = {"½":0.5,"¼":0.25,"¾":0.75,"⅓":1/3,"⅔":2/3,"⅛":0.125}

UNIT_WORDS = {
    "tsp","teaspoon","teaspoons","tbsp","tablespoon","tablespoons",
    "cup","cups","g","gram","grams","kg","oz","ounce","ounces",
    "lb","lbs","pound","pounds","ml","l","liter","liters",
    "clove","cloves","slice","slices","pinch","dash","sprig","sprigs",
    "can","cans","bunch","bunches","head","heads","stick","sticks",
}

CATEGORY_KEYWORDS = {
    "produce": ["onion","garlic","tomato","apple","peach","pear","lemon","lime",
                "orange","carrot","celery","fennel","cucumber","radish","kale",
                "spinach","mushroom","squash","potato","leek","shallot","parsley",
                "cilantro","mint","basil","dill","thyme","rosemary","ginger",
                "broccoli","cauliflower","cabbage","lettuce","avocado","corn",
                "peas","asparagus","zucchini","eggplant","banana","scallion"],
    "meat":    ["chicken","beef","pork","lamb","turkey","sausage","bacon",
                "prosciutto","pancetta","steak","ribs","ham","duck","ground"],
    "seafood": ["shrimp","salmon","tuna","cod","halibut","clam","mussel",
                "scallop","anchovy","sardine","crab","oyster","fish"],
    "dairy":   ["butter","milk","cream","cheese","yogurt","ricotta","mozzarella",
                "parmesan","feta","cheddar","egg","paneer"],
    "pantry":  ["salt","pepper","oil","vinegar","flour","sugar","honey","miso",
                "soy","rice","pasta","noodle","bean","lentil","chickpea",
                "spice","cinnamon","cumin","paprika","oregano","baking","yeast",
                "breadcrumb","panko","cocoa","chocolate","vanilla","syrup"],
    "bakery":  ["bread","bun","tortilla","pita","baguette","loaf","dough"],
}


def _parse_quantity(text):
    text = text.strip()

    m = re.match(r"^(\d+)\s+(\d+)/(\d+)", text)
    if m:
        return int(m.group(1)) + int(m.group(2))/int(m.group(3)), text[m.end():]

    m = re.match(r"^(\d+)/(\d+)", text)
    if m:
        return int(m.group(1))/int(m.group(2)), text[m.end():]

    if text and text[0] in UNICODE_FRACTIONS:
        return UNICODE_FRACTIONS[text[0]], text[1:]

    m = re.match(r"^(\d+\.?\d*)", text)
    if m:
        return float(m.group(1)), text[m.end():]

    return None, text


def _category_for(item):
    item_l = (item or "").lower()
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in item_l for w in words):
            return cat
    return "other"


def parse_ingredient(raw):
    text = str(raw).strip()

    qty, rest = _parse_quantity(text)
    rest = rest.lstrip(" .")

    unit = None
    tokens = rest.split()
    if tokens and tokens[0].rstrip(".").lower() in UNIT_WORDS:
        unit = tokens[0].rstrip(".").lower()
        rest = " ".join(tokens[1:])

    notes = None
    if "," in rest:
        item, notes = rest.split(",", 1)
        item, notes = item.strip(), notes.strip()
    else:
        item = rest.strip()

    item = re.sub(r"\(.*?\)", "", item).strip()
    cleaned = clean_ingredient(item) or item.lower()

    return {
        "item":     cleaned,
        "display":  item,
        "quantity": qty,
        "unit":     unit,
        "notes":    notes,
        "category": _category_for(cleaned),
    }


def parse_ingredient_list(raw):
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        items = ast.literal_eval(raw)
        if not isinstance(items, list):
            return []
    except (ValueError, SyntaxError):
        return []
    return [parse_ingredient(x) for x in items]