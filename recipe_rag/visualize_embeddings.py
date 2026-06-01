# recipe_rag/visualize_embeddings.py
"""Visualize the recipe vectors with TSNE.
Saves embedding_plot.png alongside this file for use in the Streamlit UI.
"""

from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from sklearn.manifold import TSNE
except ImportError:
    raise RuntimeError("scikit-learn is required: pip install scikit-learn")

from .vector_store import load_vector_store


def main() -> None:
    # ── locate the vector store (same .emb used by the app) ──────────────────
    store_path = Path(__file__).parent.parent / "artifacts" / "recipes.emb"
    if not store_path.exists():
        raise FileNotFoundError(
            f"Vector store not found at {store_path}\n"
            "Run: python scripts/build_index.py"
        )

    docs = load_vector_store(store_path)

    # ── extract embeddings & titles ───────────────────────────────────────────
    embeddings = np.stack([doc["embedding"] for doc in docs])
    titles = [
        doc.get("metadata", {}).get("title", f"recipe_{i}")[:28]
        for i, doc in enumerate(docs)
    ]

    # ── TSNE ─────────────────────────────────────────────────────────────────
    perplexity = min(30, len(docs) - 1)
    tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity, max_iter=1000)
    reduced = tsne.fit_transform(embeddings)

    # ── dark-themed plot ──────────────────────────────────────────────────────
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(13, 9))
    fig.patch.set_facecolor("#0d1b22")
    ax.set_facecolor("#0d1b22")

    scatter = ax.scatter(
        reduced[:, 0], reduced[:, 1],
        c=np.arange(len(docs)),
        cmap="plasma",
        s=55, alpha=0.85,
        edgecolors="none",
    )
    for i, (x, y) in enumerate(reduced):
        ax.text(x, y + 0.9, titles[i],
                fontsize=7, ha="center", va="bottom",
                color="#cccccc",
                alpha=0.70)

    ax.set_title("Recipe Embedding Space  (TSNE)", fontsize=14,
                 color="#f0c040", pad=14, fontweight="bold")
    ax.set_xlabel("Dimension 1", color="grey")
    ax.set_ylabel("Dimension 2", color="grey")
    ax.tick_params(colors="grey")
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")

    plt.colorbar(scatter, ax=ax, label="Recipe index")
    plt.tight_layout()

    out_path = Path(__file__).parent / "embedding_plot.png"
    plt.savefig(out_path, dpi=160, facecolor=fig.get_facecolor())
    print(f"✅  Embedding plot saved → {out_path}")


if __name__ == "__main__":
    main()
