"""
shopping_list.py
----------------
Generates a shopping list by aggregating ingredients across
every recipe in a week's meal plan.
"""

from db import get_db
from ingredient_parser import parse_ingredient_list

USER_ID = 1


def _lookup_recipe(df, recipe_id):
    try:
        return df.loc[int(recipe_id)]
    except (KeyError, ValueError):
        return None


def generate_from_plan(df, week_start, ingredients_col="Ingredients"):
    """Build (or rebuild) a shopping list for the given week.

    Regenerating the auto items on every page load used to wipe and
    recreate every auto row (fresh ids, is_checked reset to 0), which
    silently discarded whatever the user had just checked off. We now
    remember which items were checked (keyed by item name + unit)
    before wiping, and re-apply that checked state to the freshly
    generated rows so ticking a box actually sticks.
    """
    conn = get_db()
    c = conn.cursor()

    # 0. remember which auto items were checked before we wipe them
    c.execute("""
        SELECT item, unit, is_checked FROM shopping_list_items
        WHERE user_id=? AND week_start=? AND source='auto'
    """, (USER_ID, week_start))
    previously_checked = {
        (r["item"], r["unit"] or "") for r in c.fetchall() if r["is_checked"]
    }

    # 1. fetch all meal-plan entries for the week
    c.execute("""
        SELECT e.recipe_id
        FROM meal_plan_entries e
        JOIN meal_plans p ON p.id = e.meal_plan_id
        WHERE p.user_id=? AND p.week_start=?
    """, (USER_ID, week_start))
    entries = c.fetchall()

    # 2. aggregate ingredients
    basket = {}
    for e in entries:
        row = _lookup_recipe(df, e["recipe_id"])
        if row is None:
            continue
        raw = row.get(ingredients_col)
        if not isinstance(raw, str):
            continue
        for ing in parse_ingredient_list(raw):
            key = (ing["item"], ing["unit"] or "")
            if key not in basket:
                basket[key] = {
                    "item":     ing["item"],
                    "display":  ing["display"],
                    "unit":     ing["unit"],
                    "category": ing["category"],
                    "quantity": 0.0,
                }
            basket[key]["quantity"] += float(ing["quantity"] or 0)

    # 3. wipe old auto items for this week, rewrite (carrying over is_checked)
    c.execute("""
        DELETE FROM shopping_list_items
        WHERE user_id=? AND week_start=? AND source='auto'
    """, (USER_ID, week_start))
    for v in basket.values():
        key = (v["display"], v["unit"] or "")
        was_checked = 1 if key in previously_checked else 0
        c.execute("""
            INSERT INTO shopping_list_items
                (user_id, week_start, item, quantity, unit, category, source, is_checked)
            VALUES (?, ?, ?, ?, ?, ?, 'auto', ?)
        """, (USER_ID, week_start, v["display"], v["quantity"],
              v["unit"], v["category"], was_checked))
    conn.commit()

    # 4. return everything (auto + manual), sorted by aisle
    c.execute("""
        SELECT * FROM shopping_list_items
        WHERE user_id=? AND week_start=?
        ORDER BY category, item
    """, (USER_ID, week_start))
    items = [dict(r) for r in c.fetchall()]
    conn.close()
    return items


def toggle_checked(item_id, checked):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE shopping_list_items SET is_checked=? WHERE id=?",
              (1 if checked else 0, item_id))
    conn.commit()
    conn.close()


def add_manual_item(week_start, item, quantity=None, unit=None, category="other"):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO shopping_list_items
            (user_id, week_start, item, quantity, unit, category, source)
        VALUES (?, ?, ?, ?, ?, ?, 'manual')
    """, (USER_ID, week_start, item, quantity, unit, category))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def delete_item(item_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM shopping_list_items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


def uncheck_all(week_start):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE shopping_list_items SET is_checked=0
        WHERE user_id=? AND week_start=?
    """, (USER_ID, week_start))
    conn.commit()
    conn.close()