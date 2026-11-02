"""
db.py
-----
SQLite database for meal plans and shopping lists.
Recipes stay in memory (via RecipeRecommender.df).
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/app.db")


def get_db():
    """Open a connection to the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist yet."""
    conn = get_db()
    c = conn.cursor()

    # ---------- meal plans ----------
    c.execute("""
    CREATE TABLE IF NOT EXISTS meal_plans (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL DEFAULT 1,
        week_start  TEXT NOT NULL,
        UNIQUE (user_id, week_start)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS meal_plan_entries (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_plan_id  INTEGER NOT NULL,
        recipe_id     INTEGER NOT NULL,
        day_of_week   INTEGER NOT NULL,
        meal_slot     TEXT NOT NULL,
        servings      INTEGER DEFAULT 2,
        UNIQUE (meal_plan_id, day_of_week, meal_slot),
        FOREIGN KEY (meal_plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE
    )
    """)

    # ---------- shopping list ----------
    c.execute("""
    CREATE TABLE IF NOT EXISTS shopping_list_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL DEFAULT 1,
        week_start  TEXT NOT NULL,
        item        TEXT NOT NULL,
        quantity    REAL,
        unit        TEXT,
        category    TEXT,
        is_checked  INTEGER DEFAULT 0,
        in_pantry   INTEGER DEFAULT 0,
        source      TEXT DEFAULT 'auto'
    )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {DB_PATH}")