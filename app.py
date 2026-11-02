
"""
app.py
------
Flask web app: recipe search + meal planner + shopping list.
Prevents adding meals to dates before today in Karachi.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    send_from_directory,
)

from recommend import RecipeRecommender
from db import init_db
import meal_planner
import shopping_list


# ---------- Setup ----------

app = Flask(__name__)
init_db()

KARACHI_TZ = ZoneInfo("Asia/Karachi")
VALID_SLOTS = {"breakfast", "lunch", "dinner"}


# ---------- Date helpers ----------

def _today():
    """Return today's date in Karachi."""
    return datetime.now(KARACHI_TZ).date()


def _this_monday():
    """Return Monday of the current week in Karachi."""
    today = _today()
    return today - timedelta(days=today.weekday())


def _normalise_week(value):
    """Convert a supplied date into the Monday of that week."""
    try:
        selected_date = date.fromisoformat(str(value))
    except (TypeError, ValueError):
        selected_date = _today()

    return selected_date - timedelta(days=selected_date.weekday())


def _selected_date(week, day):
    """Get the actual date represented by a week and day index."""
    if day is None or day not in range(7):
        return None

    return week + timedelta(days=day)


def _is_allowed_meal_date(week, day):
    """Allow meals today or in the future, but not in the past."""
    selected_date = _selected_date(week, day)
    return selected_date is not None and selected_date >= _today()


def _wants_json():
    """Check whether the request expects a JSON response."""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _get_recipe_by_id(recipe_id):
    """Look up a recipe by its dataframe index."""
    try:
        row = recommender.df.loc[int(recipe_id)]
    except (KeyError, ValueError, TypeError):
        return None

    return {
        "id": int(recipe_id),
        "title": row.get("title"),
        "image_path": row.get("image_path"),
        "instructions": row.get("instructions"),
    }


# ---------- Dataset config ----------

USE_REAL_DATASET = True

if USE_REAL_DATASET:
    recommender = RecipeRecommender(
        data_path="data/recipes_with_images.csv",
        ingredients_col="Ingredients",
        title_col="Title",
        image_col="Image_Name",
        image_folder="food_images",
        instructions_col="Instructions",
    )
else:
    recommender = RecipeRecommender()


# ---------- Image serving ----------

@app.route("/food_images/<path:filename>")
def food_image(filename):
    return send_from_directory("static/food_images", filename)


# ---------- Recipe search ----------

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    substituted = None
    main_ingredient = ""
    others_raw = ""

    if request.method == "POST":
        main_ingredient = request.form.get(
            "main_ingredient", ""
        ).strip()

        others_raw = request.form.get(
            "other_ingredients", ""
        ).strip()

        others = [
            item.strip()
            for item in others_raw.split(",")
            if item.strip()
        ]

        if main_ingredient:
            results, substituted = recommender.recommend(
                main_ingredient,
                others,
                top_k=5,
            )

    return render_template(
        "index.html",
        results=results,
        substituted=substituted,
        main_ingredient=main_ingredient,
        other_ingredients=others_raw,
        week=_this_monday().isoformat(),
        today=_today(),
    )


# ---------- Meal plan page ----------

@app.route("/meal-plan")
def meal_plan_page():
    today = _today()
    week_dt = _normalise_week(
        request.args.get("week", _this_monday().isoformat())
    )

    week = week_dt.isoformat()
    prev_week = (week_dt - timedelta(days=7)).isoformat()
    next_week = (week_dt + timedelta(days=7)).isoformat()

    # Create the actual dates from Monday to Sunday.
    days = []

    for i in range(7):
        current_date = week_dt + timedelta(days=i)

        days.append({
            "date": current_date,
            "label": current_date.strftime("%a %d %b"),
            "is_past": current_date < today,
        })

    entries = meal_planner.get_week(week)

    for entry in entries:
        info = _get_recipe_by_id(entry["recipe_id"])
        entry["title"] = (
            info["title"] if info else "Unknown recipe"
        )

    grid = {
        (entry["day_of_week"], entry["meal_slot"]): entry
        for entry in entries
    }

    return render_template(
        "meal_plan.html",
        week=week,
        prev_week=prev_week,
        next_week=next_week,
        grid=grid,
        days=days,
        today=today,
        slots=["breakfast", "lunch", "dinner"],
    )


# ---------- Add meal from the meal planner ----------

@app.route("/meal-plan/add", methods=["POST"])
def meal_plan_add():
    week_dt = _normalise_week(
        request.form.get("week", _this_monday().isoformat())
    )

    week = week_dt.isoformat()
    recipe_id = request.form.get("recipe_id", type=int)
    day = request.form.get("day", type=int)
    slot = request.form.get("slot", "").strip().lower()

    if (
        recipe_id is None
        or day is None
        or day not in range(7)
        or slot not in VALID_SLOTS
    ):
        return redirect(
            url_for("meal_plan_page", week=week)
        )

    # Reject past dates on the server.
    if not _is_allowed_meal_date(week_dt, day):
        return redirect(
            url_for("meal_plan_page", week=week)
        )

    if _get_recipe_by_id(recipe_id) is None:
        return redirect(
            url_for("meal_plan_page", week=week)
        )

    meal_planner.add_recipe(
        week,
        recipe_id,
        day,
        slot,
    )

    return redirect(
        url_for("meal_plan_page", week=week)
    )


# ---------- Remove meal ----------

@app.route("/meal-plan/remove", methods=["POST"])
def meal_plan_remove():
    week_dt = _normalise_week(
        request.form.get("week", _this_monday().isoformat())
    )

    week = week_dt.isoformat()
    day = request.form.get("day", type=int)
    slot = request.form.get("slot", "").strip().lower()

    if day is not None and day in range(7) and slot in VALID_SLOTS:
        meal_planner.remove_entry(week, day, slot)

    return redirect(
        url_for("meal_plan_page", week=week)
    )


# ---------- Shopping list ----------

@app.route("/shopping-list")
def shopping_list_page():
    week = _normalise_week(
        request.args.get("week", _this_monday().isoformat())
    ).isoformat()

    items = shopping_list.generate_from_plan(
        recommender.df, week
    )

    grouped = {}

    for item in items:
        grouped.setdefault(
            item["category"] or "other", []
        ).append(item)

    return render_template(
        "shopping_list.html",
        week=week,
        grouped=grouped,
        total=len(items),
        checked=sum(
            1 for item in items if item["is_checked"]
        ),
    )


@app.route("/shopping-list/add", methods=["POST"])
def shopping_list_add():
    week = _normalise_week(
        request.form.get("week", _this_monday().isoformat())
    ).isoformat()

    item = request.form.get("item", "").strip()
    qty = request.form.get("quantity") or None

    if qty:
        try:
            qty = float(qty)
        except (ValueError, TypeError):
            qty = None

    new_id = None

    if item:
        new_id = shopping_list.add_manual_item(
            week, item, qty
        )

    if _wants_json():
        return jsonify(
            ok=bool(item),
            id=new_id,
            item=item,
            quantity=qty,
        )

    return redirect(
        url_for("shopping_list_page", week=week)
    )


@app.route("/shopping-list/delete", methods=["POST"])
def shopping_list_delete():
    week = _normalise_week(
        request.form.get("week", _this_monday().isoformat())
    ).isoformat()

    item_id = request.form.get("item_id", type=int)

    if item_id is not None:
        shopping_list.delete_item(item_id)

    if _wants_json():
        return jsonify(ok=True, id=item_id)

    return redirect(
        url_for("shopping_list_page", week=week)
    )


@app.route("/shopping-list/toggle", methods=["POST"])
def shopping_list_toggle():
    week = _normalise_week(
        request.form.get("week", _this_monday().isoformat())
    ).isoformat()

    item_id = request.form.get("item_id", type=int)
    checked = request.form.get("checked", "0") == "1"

    if item_id is not None:
        shopping_list.toggle_checked(item_id, checked)

    if _wants_json():
        return jsonify(
            ok=True,
            id=item_id,
            checked=checked,
        )

    return redirect(
        url_for("shopping_list_page", week=week)
    )


@app.route("/shopping-list/uncheck-all", methods=["POST"])
def shopping_list_uncheck():
    week = _normalise_week(
        request.form.get("week", _this_monday().isoformat())
    ).isoformat()

    shopping_list.uncheck_all(week)

    if _wants_json():
        return jsonify(ok=True)

    return redirect(
        url_for("shopping_list_page", week=week)
    )


# ---------- Add recipe from recipe search ----------

@app.route("/add-to-meal-plan", methods=["POST"])
def add_to_meal_plan():
    """Add a searched recipe to a valid date in the current week."""

    title = request.form.get("title", "").strip()
    day = request.form.get("day", type=int)
    slot = request.form.get("slot", "dinner").strip().lower()

    if day is None or day not in range(7):
        return redirect(url_for("index"))

    if slot not in VALID_SLOTS:
        return redirect(url_for("index"))

    # Always use the current week for recipe-search additions.
    week_dt = _this_monday()

    # Do not add to any day before today.
    if not _is_allowed_meal_date(week_dt, day):
        return redirect(
            url_for("meal_plan_page", week=week_dt.isoformat())
        )

    match = recommender.df[
        recommender.df["title"] == title
    ]

    if match.empty:
        return redirect(url_for("index"))

    recipe_id = int(match.index[0])

    meal_planner.add_recipe(
        week_dt.isoformat(),
        recipe_id,
        day,
        slot,
    )

    return redirect(
        url_for("meal_plan_page", week=week_dt.isoformat())
    )


# ---------- Debug helper ----------

@app.route("/api/recipe-id-by-title")
def api_recipe_id_by_title():
    """Look up a recipe ID by its title."""
    title = request.args.get("title", "")

    match = recommender.df[
        recommender.df["title"] == title
    ]

    if match.empty:
        return jsonify(id=None)

    return jsonify(id=int(match.index[0]))


# ---------- Run app ----------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
