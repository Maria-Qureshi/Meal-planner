"""
recommend.py
------------
Given a main ingredient + a list of other available ingredients, returns
ranked recipe suggestions using the trained ingredient embeddings.
"""

import numpy as np
from numpy.linalg import norm
from preprocess import load_recipes, clean_ingredient

DATA_PATH = "data/sample_recipes.csv"
EMBEDDINGS_PATH = "embeddings.npz"


class RecipeRecommender:
    def __init__(self, data_path=DATA_PATH, embeddings_path=EMBEDDINGS_PATH,
                 ingredients_col="ingredients", title_col="title",
                 image_col=None, image_folder=None, instructions_col=None):
        self.df = load_recipes(
            data_path,
            ingredients_col=ingredients_col,
            title_col=title_col,
            image_col=image_col,
            image_folder=image_folder,
            instructions_col=instructions_col,
        )
        data = np.load(embeddings_path, allow_pickle=True)
        self.embeddings = data["embeddings"]
        self.vocab = list(data["vocab"])
        self.word_to_idx = {w: i for i, w in enumerate(self.vocab)}

    def _vector(self, word):
        idx = self.word_to_idx.get(word)
        return self.embeddings[idx] if idx is not None else None

    def _similarity(self, word_a, word_b):
        if word_a == word_b:
            return 1.0
        va, vb = self._vector(word_a), self._vector(word_b)
        if va is None or vb is None:
            return 0.0
        return float(va @ vb / (norm(va) * norm(vb) + 1e-10))

    def _best_substitute(self, word, k=1):
        return None

    def recommend(self, main_ingredient, other_ingredients, top_k=5):
        main_clean = clean_ingredient(main_ingredient)
        if main_clean is None:
            main_clean = main_ingredient.strip().lower()

        others_clean = []
        for i in other_ingredients:
            if not i.strip():
                continue
            c = clean_ingredient(i)
            others_clean.append(c if c else i.strip().lower())

        user_ingredients = set([main_clean] + others_clean)

        exact_matches = self.df[self.df["ingredients_clean"].apply(
            lambda lst: main_clean in lst
        )]

        if len(exact_matches) > 0:
            pool = exact_matches
            substituted = None
        else:
            substituted = self._best_substitute(main_clean)
            if substituted:
                pool = self.df[self.df["ingredients_clean"].apply(
                    lambda lst: substituted in lst
                )]
            else:
                pool = self.df

        if len(pool) == 0:
            return [], substituted

        results = []
        for _, row in pool.iterrows():
            recipe_ings = row["ingredients_clean"]
            score, missing = self._score_recipe(user_ingredients, recipe_ings)
            results.append({
                "title": row["title"],
                "cuisine": row.get("cuisine", None),
                "image_path": row.get("image_path", None),
                "instructions": row.get("instructions", None),
                "score": round(score, 3),
                "have": sorted(user_ingredients & set(recipe_ings)),
                "missing": missing,
            })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k], substituted

    def _score_recipe(self, user_ingredients, recipe_ings):
        if not recipe_ings:
            return 0.0, []

        per_ingredient_scores = []
        missing = []
        for r_ing in recipe_ings:
            best = 0.0
            for u_ing in user_ingredients:
                best = max(best, self._similarity(r_ing, u_ing))
            per_ingredient_scores.append(best)
            if best < 0.6:
                missing.append(r_ing)

        avg_score = float(np.mean(per_ingredient_scores))
        return avg_score, missing


if __name__ == "__main__":
    rec = RecipeRecommender()
    results, substituted = rec.recommend(
        main_ingredient="chicken breast",
        other_ingredients=["garlic", "tomato", "pasta"]
    )
    if substituted:
        print(f"(no exact match for main ingredient, substituted: {substituted})")
    for r in results:
        print(f"\n{r['title']}  [score={r['score']}]  ({r['cuisine']})")
        print(f"  have:    {r['have']}")
        print(f"  missing: {r['missing']}")