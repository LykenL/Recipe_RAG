import streamlit as st
from pathlib import Path
import base64

_ROOT = Path(__file__).resolve().parent
_VECTOR_STORE_CANDIDATES = (
    _ROOT / "artifacts" / "recipes.emb",
    _ROOT / "week_3" / "COLX_563_lab3_Lyken35" / "recipes.emb",
)


def _resolve_vector_store() -> Path:
    for path in _VECTOR_STORE_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Vector store not found. Expected artifacts/recipes.emb — "
        "run: python scripts/build_index.py"
    )


@st.cache_resource(show_spinner="Loading recipe index and embedding model…")
def _load_assistant():
    from recipe_rag.app import RecipeRAGAssistant
    from recipe_rag.config import hydrate_config_from_streamlit_secrets, load_env

    hydrate_config_from_streamlit_secrets()
    env_file = _ROOT / ".env"
    load_env(env_file if env_file.is_file() else None)
    return RecipeRAGAssistant.from_files(
        vector_store_path=_resolve_vector_store(),
        dotenv_path=None,
        embedding_model="all-MiniLM-L6-v2",
    )


# ── Load background image as base64 ──────────────────────────────────────────
def _get_bg() -> str:
    txt = _ROOT / "bg_b64.txt"
    if txt.exists():
        return txt.read_text().strip()
    return ""


# ── CSS (plain string, no f-string – avoids { } conflicts) ───────────────────
# __BG__ is replaced at runtime with the base64 data URI.
_CSS_TEMPLATE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@300;400;500;600&display=swap');

/* ── full-screen background ── */
.stApp {
    background-image: url("data:image/png;base64,__BG__");
    background-size: cover;
    background-position: center center;
    background-attachment: fixed;
    font-family: 'Inter', sans-serif;
}

/* dark gradient overlay */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background: linear-gradient(
        135deg,
        rgba(8,18,24,0.90)  0%,
        rgba(12,28,38,0.84) 45%,
        rgba(30,16,8,0.82) 100%
    );
    z-index: 0;
    pointer-events: none;
}

/* content sits above overlay */
.main .block-container {
    position: relative;
    z-index: 1;
    padding-top: 1.5rem;
    max-width: 820px;
}

/* ── hero ── */
.hero {
    text-align: center;
    padding: 2.8rem 1rem 2.2rem;
}
.hero-emoji {
    font-size: 3.8rem;
    display: block;
    margin-bottom: 0.35rem;
    filter: drop-shadow(0 0 18px rgba(220,150,60,0.75));
    animation: float 3s ease-in-out infinite;
}
@keyframes float {
    0%,100% { transform: translateY(0);   }
    50%      { transform: translateY(-9px); }
}
.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.7rem;
    font-weight: 700;
    color: #f7f4ee !important;
    letter-spacing: -0.4px;
    line-height: 1.1;
    margin: 0;
    text-shadow: 0 1px 28px rgba(255, 248, 235, 0.35),
                 0 2px 12px rgba(0, 0, 0, 0.25);
}
.hero .hero-title {
    color: #f7f4ee !important;
}
.hero-subtitle {
    margin-top: 0.7rem;
    font-size: 0.97rem;
    color: rgba(255,255,255,0.50);
    font-weight: 300;
    letter-spacing: 0.4px;
}
.accent-line {
    width: 58px;
    height: 3px;
    background: linear-gradient(90deg, #e07b2a, #f0c040);
    border-radius: 2px;
    margin: 1.1rem auto 0;
}

/* ── glass card ── */
.glass-card {
    background: rgba(255,255,255,0.055);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.11);
    border-radius: 20px;
    padding: 2rem 2.2rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.45);
}

/* ── form labels ── */
.stTextArea label,
.stSelectbox label {
    color: rgba(255,255,255,0.70) !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.9px !important;
    text-transform: uppercase !important;
}

/* ── textarea (dark input surface) ── */
.stTextArea > div > div > textarea,
.stTextArea textarea {
    background: rgba(8, 14, 20, 0.92) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 13px !important;
    color: #f2f6fa !important;
    font-size: 0.98rem !important;
    font-family: 'Inter', sans-serif !important;
    caret-color: #f0c040;
    transition: border 0.25s, box-shadow 0.25s;
}
.stTextArea > div > div {
    background: transparent !important;
}
.stTextArea textarea:focus {
    border: 1px solid rgba(220,150,60,0.55) !important;
    box-shadow: 0 0 0 3px rgba(220,150,60,0.12) !important;
    outline: none !important;
    background: rgba(6, 12, 18, 0.96) !important;
}
.stTextArea textarea::placeholder {
    color: rgba(255,255,255,0.32) !important;
}

/* ── selectbox ── */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 13px !important;
    color: #ffffff !important;
}

/* ── primary button ── */
div.stButton > button {
    background: linear-gradient(135deg, #e07b2a 0%, #f0c040 100%) !important;
    color: #111111 !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    letter-spacing: 0.4px !important;
    border: none !important;
    border-radius: 13px !important;
    padding: 0.7rem 2.2rem !important;
    width: 100% !important;
    cursor: pointer !important;
    box-shadow: 0 4px 22px rgba(220,130,40,0.40) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
div.stButton > button:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 10px 30px rgba(220,130,40,0.60) !important;
}
div.stButton > button:active {
    transform: translateY(-1px) !important;
}

/* ── answer card ── */
.answer-card {
    background: rgba(220,150,60,0.07);
    border-left: 4px solid #e07b2a;
    border-radius: 0 14px 14px 0;
    padding: 1.3rem 1.5rem;
    color: rgba(255,255,255,0.88);
    font-size: 1rem;
    line-height: 1.75;
    margin-top: 0.4rem;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: anywhere;
}

/* ── section label ── */
.section-label {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: #e07b2a;
    margin-bottom: 0.6rem;
}

/* ── image caption ── */
.stImage > div > p {
    color: rgba(255,255,255,0.38) !important;
    font-size: 0.78rem !important;
    text-align: center;
}

/* ── spinner / alerts ── */
.stSpinner > div {
    border-top-color: #e07b2a !important;
}
.stAlert {
    background: rgba(255,255,255,0.05) !important;
    border-radius: 12px !important;
    color: rgba(255,255,255,0.70) !important;
}

/* ── expander (advanced viz) ── */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 12px !important;
    color: rgba(255,255,255,0.55) !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.3px;
}
details[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    margin-top: 0.5rem;
}
details[data-testid="stExpander"] > div {
    border-top: 1px solid rgba(255,255,255,0.06);
}

/* ── hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
</style>
"""


def _render_embedding_viz() -> None:
    """Optional TSNE plot for technical users; hidden in a collapsed expander."""
    plot_path = Path(__file__).parent / "recipe_rag" / "embedding_plot.png"
    with st.expander(
        "Advanced — recipe embedding map (optional)",
        expanded=False,
    ):
        st.caption(
            "A 2D view of how recipes sit in vector space. "
            "Only needed if you are exploring the RAG pipeline."
        )
        if plot_path.is_file():
            st.image(
                str(plot_path),
                caption="t-SNE projection of recipe embeddings",
                use_container_width=True,
            )
        else:
            st.markdown(
                "No plot yet. Generate one with: "
                "`python -m recipe_rag.visualize_embeddings`"
            )


def inject_theme() -> None:
    bg = _get_bg()
    css = _CSS_TEMPLATE.replace("__BG__", bg)
    st.markdown(css, unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="RecipeRAG · AI Chef",
        page_icon="🍳",
        layout="centered",
    )
    inject_theme()

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero">
        <span class="hero-emoji">🍳</span>
        <h1 class="hero-title">Recipe Intelligence</h1>
        <p class="hero-subtitle">
            Retrieval-Augmented Generation &nbsp;·&nbsp;
            Vector search &amp; large language models
        </p>
        <div class="accent-line"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Input card ────────────────────────────────────────────────────────────
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)

    query = st.text_area(
        "Your Question",
        placeholder="e.g.  How many cups of flour do I need for 2 servings of pasta?",
        height=110,
        key="query",
    )
    model_option = st.selectbox(          # noqa: F841  (used as display only for now)
        "LLM Backend",
        ["openai", "gemini", "claude"],
        index=0,
    )
    ask = st.button("✨  Ask the Chef", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Answer ────────────────────────────────────────────────────────────────
    if ask and query.strip():
        from recipe_rag.formatting import answer_to_html

        with st.spinner("Searching recipes and generating answer…"):
            try:
                answer = _load_assistant().route(query)
            except Exception as exc:
                answer = f"⚠️  {exc}"

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<p class="section-label">Chef\'s Answer</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="answer-card">{answer_to_html(answer)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Optional embedding viz (collapsed by default) ───────────────────────
    _render_embedding_viz()


if __name__ == "__main__":
    main()
