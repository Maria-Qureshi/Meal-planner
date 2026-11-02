"""
train_embeddings.py
--------------------
Trains ingredient embeddings from scratch using Word2Vec's skip-gram
architecture with negative sampling, implemented in plain NumPy.
"""

import numpy as np
from preprocess import load_recipes

# --- Dataset config (must match app.py) ---
USE_REAL_DATASET = True
DATA_PATH = "data/recipes_with_images.csv" if USE_REAL_DATASET else "data/sample_recipes.csv"
INGREDIENTS_COL = "Ingredients" if USE_REAL_DATASET else "ingredients"
TITLE_COL = "Title" if USE_REAL_DATASET else "title"

# Cap vocabulary to the N most common ingredients -- real datasets have
# thousands of messy/rare ingredient strings, and training on all of them
# is slow and mostly noise. None = no cap.
MAX_VOCAB = 800

EMBEDDING_DIM = 32
EPOCHS = 50          # lower than before since real datasets have far more pairs
LEARNING_RATE = 0.05
NEGATIVE_SAMPLES = 5
SEED = 42


def build_vocab(ingredient_lists, max_vocab=None):
    from collections import Counter
    counts = Counter(ing for lst in ingredient_lists for ing in lst)
    if max_vocab:
        vocab = [w for w, _ in counts.most_common(max_vocab)]
    else:
        vocab = sorted(counts.keys())
    word_to_idx = {w: i for i, w in enumerate(vocab)}
    return vocab, word_to_idx


def build_training_pairs(ingredient_lists, word_to_idx):
    pairs = []
    for lst in ingredient_lists:
        idxs = [word_to_idx[w] for w in lst if w in word_to_idx]
        for i, center in enumerate(idxs):
            for j, context in enumerate(idxs):
                if i != j:
                    pairs.append((center, context))
    return pairs


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def train(pairs, vocab_size, dim=EMBEDDING_DIM, epochs=EPOCHS,
          lr=LEARNING_RATE, neg_samples=NEGATIVE_SAMPLES, seed=SEED):
    rng = np.random.default_rng(seed)
    W_in = rng.normal(0, 0.1, size=(vocab_size, dim))
    W_out = rng.normal(0, 0.1, size=(vocab_size, dim))

    pairs = np.array(pairs)
    losses = []

    for epoch in range(epochs):
        rng.shuffle(pairs)
        total_loss = 0.0

        for center, context in pairs:
            v_center = W_in[center]
            v_context = W_out[context]

            score = sigmoid(np.dot(v_center, v_context))
            grad = (score - 1.0)
            grad_center = grad * v_context
            grad_context = grad * v_center
            total_loss += -np.log(score + 1e-10)

            neg_idxs = rng.integers(0, vocab_size, size=neg_samples)
            for neg in neg_idxs:
                v_neg = W_out[neg]
                neg_score = sigmoid(np.dot(v_center, v_neg))
                grad_center += neg_score * v_neg
                W_out[neg] -= lr * neg_score * v_center
                total_loss += -np.log(1 - neg_score + 1e-10)

            W_in[center] -= lr * grad_center
            W_out[context] -= lr * grad_context

        losses.append(total_loss / len(pairs))
        print(f"epoch {epoch:3d}  avg loss {losses[-1]:.4f}")

    return (W_in + W_out) / 2, losses


def main():
    df = load_recipes(DATA_PATH, ingredients_col=INGREDIENTS_COL, title_col=TITLE_COL)
    ingredient_lists = df["ingredients_clean"].tolist()

    vocab, word_to_idx = build_vocab(ingredient_lists, max_vocab=MAX_VOCAB)
    print(f"Vocabulary size: {len(vocab)} ingredients")

    pairs = build_training_pairs(ingredient_lists, word_to_idx)
    print(f"Training pairs: {len(pairs)}")

    embeddings, losses = train(pairs, len(vocab))

    np.savez("embeddings.npz", embeddings=embeddings, vocab=np.array(vocab))
    print("Saved embeddings.npz")


if __name__ == "__main__":
    main()