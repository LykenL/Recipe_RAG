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
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

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
    background: radial-gradient(circle at 50% 0%, rgba(30,20,15,0.7) 0%, rgba(10,12,16,0.95) 70%);
    z-index: 0;
    pointer-events: none;
}

/* content sits above overlay */
.main .block-container {
    position: relative;
    z-index: 1;
    padding-top: 3rem;
    max-width: 860px;
}

/* ── hero ── */
.hero {
    text-align: center;
    padding: 2rem 1rem 3rem;
}
.hero-emoji {
    font-size: 4.5rem;
    display: block;
    margin-bottom: 0.5rem;
    filter: drop-shadow(0 10px 20px rgba(230, 140, 40, 0.4));
    animation: float 4s ease-in-out infinite;
}
@keyframes float {
    0%,100% { transform: translateY(0) scale(1);   }
    50%      { transform: translateY(-12px) scale(1.05); }
}
.hero-title {
    font-family: 'Outfit', sans-serif;
    font-size: 3.5rem;
    font-weight: 700;
    color: #ffffff !important;
    letter-spacing: -1px;
    line-height: 1.1;
    margin: 0;
    background: linear-gradient(135deg, #ffffff 0%, #f0c040 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 4px 30px rgba(240, 192, 64, 0.2);
}
.hero-subtitle {
    margin-top: 1rem;
    font-size: 1.1rem;
    color: rgba(255,255,255,0.6);
    font-weight: 300;
    letter-spacing: 0.5px;
}
.accent-line {
    width: 80px;
    height: 4px;
    background: linear-gradient(90deg, #ff7e5f, #feb47b);
    border-radius: 4px;
    margin: 1.5rem auto 0;
    box-shadow: 0 2px 10px rgba(255, 126, 95, 0.4);
}

/* ── premium glass card ── */
.glass-card {
    background: rgba(20, 25, 35, 0.4);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    padding: 2.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 16px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.glass-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 20px 50px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.15);
}

/* ── form labels ── */
.stTextArea label,
.stSelectbox label {
    color: rgba(255,255,255,0.85) !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    font-family: 'Outfit', sans-serif !important;
    margin-bottom: 0.5rem !important;
}

/* ── textarea (modern input surface) ── */
.stTextArea > div > div > textarea,
.stTextArea textarea {
    background: rgba(10, 15, 25, 0.6) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 16px !important;
    color: #ffffff !important;
    font-size: 1.05rem !important;
    font-family: 'Inter', sans-serif !important;
    padding: 1rem !important;
    caret-color: #feb47b;
    transition: all 0.3s ease !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.2) !important;
}
.stTextArea > div > div {
    background: transparent !important;
}
.stTextArea textarea:focus {
    border: 1px solid rgba(254, 180, 123, 0.6) !important;
    box-shadow: 0 0 0 4px rgba(254, 180, 123, 0.15), inset 0 2px 4px rgba(0,0,0,0.2) !important;
    outline: none !important;
    background: rgba(10, 15, 25, 0.8) !important;
}
.stTextArea textarea::placeholder {
    color: rgba(255,255,255,0.25) !important;
    font-weight: 300;
}

/* ── selectbox ── */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
    transition: all 0.3s ease !important;
}
.stSelectbox > div > div:hover {
    border-color: rgba(255,255,255,0.2) !important;
}

/* ── premium primary button ── */
div.stButton > button {
    background: linear-gradient(135deg, #ff7e5f 0%, #feb47b 100%) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 1.1rem !important;
    letter-spacing: 0.5px !important;
    border: none !important;
    border-radius: 16px !important;
    padding: 0.8rem 2.5rem !important;
    width: 100% !important;
    cursor: pointer !important;
    box-shadow: 0 8px 25px rgba(255, 126, 95, 0.3) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div.stButton > button:hover {
    transform: translateY(-4px) scale(1.01) !important;
    box-shadow: 0 15px 35px rgba(255, 126, 95, 0.5) !important;
}
div.stButton > button:active {
    transform: translateY(-1px) scale(0.99) !important;
    box-shadow: 0 5px 15px rgba(255, 126, 95, 0.3) !important;
}

/* ── answer card ── */
.answer-card {
    background: linear-gradient(180deg, rgba(254, 180, 123, 0.08) 0%, rgba(255, 126, 95, 0.03) 100%);
    border-left: 4px solid #ff7e5f;
    border-radius: 0 20px 20px 0;
    padding: 2rem;
    color: rgba(255,255,255,0.9);
    font-size: 1.05rem;
    line-height: 1.8;
    margin-top: 1rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    white-space: pre-wrap;
}
.answer-card ul, .answer-card ol {
    padding-left: 1.5rem;
    margin-top: 1rem;
    margin-bottom: 1rem;
}
.answer-card li {
    margin-bottom: 0.5rem;
}

/* ── section label ── */
.section-label {
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #feb47b;
    margin-bottom: 0.8rem;
    font-family: 'Outfit', sans-serif;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-label::before {
    content: '';
    display: block;
    width: 12px;
    height: 12px;
    background: #ff7e5f;
    border-radius: 50%;
    box-shadow: 0 0 10px rgba(255, 126, 95, 0.8);
}

/* ── image caption ── */
.stImage > div > p {
    color: rgba(255,255,255,0.4) !important;
    font-size: 0.85rem !important;
    text-align: center;
    margin-top: 0.5rem;
}

/* ── spinner / alerts ── */
.stSpinner > div {
    border-top-color: #ff7e5f !important;
}
.stAlert {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 16px !important;
    color: rgba(255,255,255,0.8) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important;
}

/* ── expander (advanced viz) ── */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 14px !important;
    color: rgba(255,255,255,0.6) !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.5px;
    font-family: 'Outfit', sans-serif !important;
    transition: all 0.3s ease !important;
}
.streamlit-expanderHeader:hover {
    background: rgba(255,255,255,0.06) !important;
    color: rgba(255,255,255,0.8) !important;
}
details[data-testid="stExpander"] {
    background: rgba(10, 15, 25, 0.4);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    margin-top: 1rem;
    overflow: hidden;
}
details[data-testid="stExpander"] > div {
    border-top: 1px solid rgba(255,255,255,0.05);
    padding: 1.5rem;
}

/* ── sidebar styling ── */
[data-testid="stSidebar"] {
    background-color: rgba(10, 12, 16, 0.95) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}
[data-testid="stSidebar"] label, 
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3, 
[data-testid="stSidebar"] span {
    color: rgba(255, 255, 255, 0.9) !important;
}

/* ── loading animation ── */
@keyframes pulse {
    0% { opacity: 0.6; transform: scale(0.98); }
    50% { opacity: 1; transform: scale(1); }
    100% { opacity: 0.6; transform: scale(0.98); }
}
.loading-text {
    animation: pulse 1.5s infinite;
    text-align: center;
    color: #feb47b;
    font-size: 1.1rem;
    font-weight: 500;
    margin: 2rem 0;
    font-family: 'Outfit', sans-serif;
    letter-spacing: 0.5px;
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

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 👨‍🍳 Chef's Settings")
        
        persona = st.selectbox(
            "Chef Persona",
            ["Friendly Home Cook", "Gordon Ramsay (Harsh & Pro)", "Nutritionist (Health-focused)"]
        )
        
        st.markdown("### 🥦 Dietary Restrictions")
        is_veg = st.checkbox("Vegetarian")
        is_gf = st.checkbox("Gluten-Free")
        is_nut_free = st.checkbox("Nut Allergy")
        
        st.markdown("### 🧊 My Pantry")
        pantry = st.multiselect(
            "What's in your fridge?",
            ["Eggs", "Milk", "Chicken", "Beef", "Salmon", "Onions", "Garlic", "Tomatoes", "Potatoes", "Pasta", "Rice", "Cheese"]
        )
        
        custom_ingredients = st.text_input("Any other ingredients?", placeholder="e.g. Soy sauce, Ginger, Pork")
        
        st.markdown("### ⚡ Quick Inspiration")
        # Use session state to automatically populate and submit
        if st.button("⏱️ Quick Dinner", use_container_width=True):
            st.session_state.query_input = "Recommend a quick and easy dinner."
            st.session_state.auto_submit = True
        if st.button("🏋️ High Protein Meal", use_container_width=True):
            st.session_state.query_input = "Recommend a high protein, low fat meal."
            st.session_state.auto_submit = True
        if st.button("🍰 No-Bake Dessert", use_container_width=True):
            st.session_state.query_input = "Recommend a dessert that doesn't require an oven."
            st.session_state.auto_submit = True

    # ── Input card ────────────────────────────────────────────────────────────
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)

    query = st.text_area(
        "Your Question",
        placeholder="e.g.  How many cups of flour do I need for 2 servings of pasta?",
        height=110,
        key="query_input",
    )

    ask = st.button("✨  Ask the Chef", use_container_width=True)
    
    if st.session_state.get("auto_submit", False):
        ask = True
        st.session_state.auto_submit = False

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Answer ────────────────────────────────────────────────────────────────
    if ask and query.strip():
        from recipe_rag.formatting import answer_to_html
        
        # Build the augmented query based on sidebar settings
        augmented_query = query.strip()
        
        if persona != "Friendly Home Cook":
            augmented_query = f"[System Instructions: Please answer in the persona of {persona}] " + augmented_query
            
        restrictions = []
        if is_veg: restrictions.append("Vegetarian")
        if is_gf: restrictions.append("Gluten-Free")
        if is_nut_free: restrictions.append("No Nuts (Allergy)")
        
        if restrictions:
            augmented_query += f"\n\nDietary Restrictions: {', '.join(restrictions)}. Please ensure the recipe strictly follows these."
            
        actual_pantry = list(pantry)
        if custom_ingredients:
            actual_pantry.extend([x.strip() for x in custom_ingredients.split(",") if x.strip()])
            
        if actual_pantry:
            augmented_query += f"\n\nI have the following ingredients available in my pantry: {', '.join(actual_pantry)}. Try to use them if possible."

        st.markdown('<div class="glass-card"><p class="section-label" id="answer-section">Chef\'s Answer</p>', unsafe_allow_html=True)
        
        # Inject JavaScript to auto-scroll to the answer section
        import streamlit.components.v1 as components
        components.html(
            """
            <script>
                var target = window.parent.document.getElementById('answer-section');
                if (target) {
                    target.scrollIntoView({behavior: 'smooth', block: 'start'});
                }
            </script>
            """,
            height=0
        )
        
        answer_placeholder = st.empty()
        
        answer_placeholder.markdown(
            '<div class="loading-text">👨‍🍳 The Chef is thinking...</div>', 
            unsafe_allow_html=True
        )
        
        full_answer = ""
        try:
            import time
            for chunk in _load_assistant().route(augmented_query):
                full_answer += chunk
                answer_placeholder.markdown(
                    f'<div class="answer-card">{answer_to_html(full_answer)}▌</div>', 
                    unsafe_allow_html=True
                )
                time.sleep(0.015)
            # 最终去掉闪烁的光标
            answer_placeholder.markdown(
                f'<div class="answer-card">{answer_to_html(full_answer)}</div>', 
                unsafe_allow_html=True
            )
        except Exception as exc:
            answer_placeholder.markdown(
                f'<div class="answer-card">⚠️ {exc}</div>', 
                unsafe_allow_html=True
            )
            
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Optional embedding viz (collapsed by default) ───────────────────────
    _render_embedding_viz()


if __name__ == "__main__":
    main()
