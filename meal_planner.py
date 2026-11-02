"""
meal_planner.py
---------------
CRUD for weekly meal plans.
"""

from db import get_db

USER_ID = 1  # swap with session user later


def _get_or_create_plan(week_start):
    """Return the meal_plan id for this user+week, creating one if needed."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO meal_plans (user_id, week_start) VALUES (?, ?)",
        (USER_ID, week_start)
    )
    conn.commit()
    c.execute(
        "SELECT id FROM meal_plans WHERE user_id=? AND week_start=?",
        (USER_ID, week_start)
    )
    plan_id = c.fetchone()["id"]
    conn.close()
    return plan_id


def add_recipe(week_start, recipe_id, day, slot):
    """Add (or replace) a recipe in the given day/slot."""
    plan_id = _get_or_create_plan(week_start)
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO meal_plan_entries
            (meal_plan_id, recipe_id, day_of_week, meal_slot)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(meal_plan_id, day_of_week, meal_slot)
        DO UPDATE SET recipe_id = excluded.recipe_id
    """, (plan_id, recipe_id, day, slot))
    conn.commit()
    conn.close()


def remove_entry(week_start, day, slot):
    """Remove whatever is in that day/slot."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        DELETE FROM meal_plan_entries
        WHERE meal_plan_id = (
            SELECT id FROM meal_plans WHERE user_id=? AND week_start=?
        )
        AND day_of_week=? AND meal_slot=?
    """, (USER_ID, week_start, day, slot))
    conn.commit()
    conn.close()


def get_week(week_start):
    """Return all entries for the week as a list of dicts."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT e.day_of_week, e.meal_slot, e.recipe_id, e.servings
        FROM meal_plan_entries e
        JOIN meal_plans p ON p.id = e.meal_plan_id
        WHERE p.user_id=? AND p.week_start=?
        ORDER BY e.day_of_week,
                 CASE e.meal_slot
                    WHEN 'breakfast' THEN 1
                    WHEN 'lunch'     THEN 2
                    WHEN 'dinner'    THEN 3
                 END
    """, (USER_ID, week_start))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def clear_week(week_start):
    """Remove everything from this week's plan."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        DELETE FROM meal_plan_entries
        WHERE meal_plan_id = (
            SELECT id FROM meal_plans WHERE user_id=? AND week_start=?
        )
    """, (USER_ID, week_start))
    conn.commit()
    conn.close()