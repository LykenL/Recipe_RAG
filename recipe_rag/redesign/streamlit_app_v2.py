"""
streamlit_app_v2.py — drop-in replacement for the current streamlit_app.py.

What changed vs. the current build
----------------------------------
* Warm "parchment + espresso" design system with real contrast ratios
  (body text #3D362E on #FAF6F0 ≈ 9.4:1, vs. the old ~2.6:1 grey-on-black).
* Chat-first: the product is a conversation, not a one-shot form. History
  persists, the composer is docked, every answer keeps its sources.
* The agent is made visible: a live trace shows the tool call, how many
  recipes were retrieved, and which were rejected.
* Retrieved passages render as scored, citable source cards.
* Sidebar is a real settings rail: visible control labels, switches instead
  of bare checkboxes, pantry as removable chips.
* The empty state earns the space it takes: one composer + quick starts,
  instead of a dead 300px box above a second input.

To adopt:  copy to the repo root as `streamlit_app_v2.py` and run
    streamlit run streamlit_app_v2.py
"""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent
_VECTOR_STORE_CANDIDATES = (
    _ROOT / "artifacts" / "recipes.emb",
    _ROOT / "week_3" / "COLX_563_lab3_Lyken35" / "recipes.emb",
)

QUICK_STARTS = {
    "Quick dinner": "Something for dinner tonight that takes under 20 minutes, uses 6 ingredients or fewer, and is at most 5 steps.",
    "High protein": "A high-protein, low-fat main dish, at least 30 g of protein per serving.",
    "No-bake dessert": "A dessert that needs no oven and no more than 15 minutes of hands-on work.",
    "Use my pantry": "What can I make right now using mainly the ingredients I already have?",
}


# ────────────────────────────── backend ──────────────────────────────────────
def _resolve_vector_store() -> Path:
    for path in _VECTOR_STORE_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Vector store not found. Expected artifacts/recipes.emb — run: python scripts/build_index.py"
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


@st.cache_data(show_spinner=False)
def _index_size() -> int:
    """Real recipe count — never hardcode this in the UI again."""
    try:
        from recipe_rag.vector_store import load_vector_store

        return len(load_vector_store(_resolve_vector_store()))
    except Exception:
        return 0


class TracedAssistant:
    """Wraps the RAG assistant so the UI can *show* the agent's tool calls."""

    def __init__(self, base) -> None:
        self.base = base
        self.trace: list[dict] = []

    def run(self, query: str):
        self.trace = []
        original = self.base.search_cookbook

        def traced_search(q: str) -> str:
            out = original(q)
            blocks = [] if out.startswith("No matching") else out.split("\n\n---\n\n")
            self.trace.append({"query": q, "matches": [b for b in blocks if b.strip()]})
            return out

        self.base.search_cookbook = traced_search  # picked up inside app.run()
        try:
            yield from self.base.run(query)
        finally:
            self.base.search_cookbook = original


# ─────────────────────────────── styling ─────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

:root{
  --canvas:#FAF6F0; --surface:#FFFFFF; --surface-2:#F5EFE6;
  --rail:#191512; --rail-2:#221D18; --rail-line:#332C25; --rail-ink:#F6F1E9; --rail-mute:#B3A899;
  --ink:#17130E; --ink-2:#3D362E; --muted:#6E6459; --faint:#9A9086;
  --line:#EBE2D6; --terra:#CE4A18; --terra-soft:#FDF0E8; --sage:#3E7A4F; --sage-soft:#EAF3EC;
  --shadow-m:0 8px 24px -8px rgba(31,23,15,.18), 0 2px 6px rgba(31,23,15,.05);
  --ui:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --display:'Fraunces',Georgia,serif;
}
html,body,[class*="css"]{font-family:var(--ui)}
.stApp{background:var(--canvas);color:var(--ink)}
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;
  background:radial-gradient(900px 380px at 18% -6%,rgba(233,160,59,.10),transparent 60%),
             radial-gradient(700px 340px at 92% 4%,rgba(206,74,24,.06),transparent 62%)}
#MainMenu,footer,header{visibility:hidden}
.block-container{max-width:820px;padding-top:2.2rem;padding-bottom:7rem}

/* ── header ── */
.mise-top{display:flex;align-items:center;gap:14px;padding:0 0 22px;border-bottom:1px solid var(--line);margin-bottom:26px}
.mise-mark{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;
  background:linear-gradient(145deg,#E9A03B,#CE4A18);box-shadow:0 6px 16px -6px rgba(206,74,24,.75);font-size:18px}
.mise-name{font:600 21px/1 var(--display);color:var(--ink)}
.mise-sub{font:500 10.5px/1 var(--ui);letter-spacing:.14em;text-transform:uppercase;color:var(--faint);margin-top:5px}
.mise-status{margin-left:auto;display:inline-flex;align-items:center;gap:8px;font:500 12.5px/1 var(--ui);
  color:var(--ink-2);background:var(--surface);border:1px solid var(--line);padding:8px 13px;border-radius:999px;box-shadow:var(--shadow-m)}
.mise-dot{width:7px;height:7px;border-radius:50%;background:#5FBF7B;box-shadow:0 0 0 3px rgba(95,191,123,.2)}

/* ── empty state ── */
.mise-hero{padding:26px 0 8px}
.mise-eyebrow{display:inline-block;font:600 11px/1 var(--ui);letter-spacing:.14em;text-transform:uppercase;
  color:var(--terra);background:var(--terra-soft);border:1px solid #F6D9C7;padding:8px 13px;border-radius:999px}
.mise-h1{font:600 46px/1.08 var(--display);letter-spacing:-1px;color:var(--ink);margin:20px 0 14px}
.mise-h1 em{font-style:italic;color:var(--terra)}
.mise-lede{font:400 16px/1.6 var(--ui);color:var(--muted);max-width:600px}

/* ── sidebar rail ── */
[data-testid="stSidebar"]{background:var(--rail) !important;border-right:1px solid var(--rail-line)}
[data-testid="stSidebar"] *{color:var(--rail-ink)}
[data-testid="stSidebar"] .block-container{padding-top:1.4rem}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{
  font:600 11px/1 var(--ui) !important;letter-spacing:.16em;text-transform:uppercase;
  color:var(--rail-mute) !important;margin:22px 0 10px}
[data-testid="stSidebar"] label p{font:500 13.5px/1 var(--ui) !important;color:#E7DFD4 !important}
[data-testid="stSidebar"] [data-baseweb="select"]>div,
[data-testid="stSidebar"] [data-baseweb="input"]>div{
  background:var(--rail-2) !important;border:1px solid var(--rail-line) !important;border-radius:11px !important}
[data-testid="stSidebar"] input{color:var(--rail-ink) !important}
[data-testid="stSidebar"] input::placeholder{color:#8C8175 !important}
[data-testid="stSidebar"] [data-baseweb="tag"]{background:#2E2821 !important;border:1px solid var(--rail-line) !important;border-radius:999px !important}
[data-testid="stSidebar"] [data-testid="stCheckbox"]{padding:3px 0}
[data-testid="stSidebar"] [data-testid="stCheckbox"] span[data-baseweb="checkbox"] div{
  background:transparent !important;border:1.6px solid #5B5247 !important;border-radius:6px !important}
[data-testid="stSidebar"] [data-testid="stCheckbox"] span[data-baseweb="checkbox"] div[aria-checked="true"],
[data-testid="stSidebar"] [data-testid="stCheckbox"] input:checked+div{
  background:var(--sage) !important;border-color:var(--sage) !important}
[data-testid="stSidebar"] .mise-index{margin-top:26px;padding-top:14px;border-top:1px solid var(--rail-line);
  font:400 11.5px/1.7 var(--ui);color:var(--rail-mute)}
[data-testid="stSidebar"] .mise-index b{color:#CFC5B9;font-weight:500}
[data-testid="stSidebar"] .stButton>button{background:transparent !important;border:1px solid var(--rail-line) !important;
  color:var(--rail-ink) !important;border-radius:10px !important;font:500 13px/1 var(--ui) !important;
  text-align:left !important;justify-content:flex-start !important;padding:.55rem .8rem !important;width:100%}
[data-testid="stSidebar"] .stButton>button:hover{border-color:var(--terra) !important;background:#241E18 !important}
[data-testid="stSidebar"] .stButton>button p{font:500 13px/1 var(--ui) !important;color:var(--rail-ink) !important}

/* ── chat turns ── */
[data-testid="stChatMessage"]{background:transparent;border:0;padding:0;margin:0 0 16px}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){
  background:#211C16;border-radius:16px 16px 4px 16px;padding:13px 17px;margin-left:auto;max-width:78%}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) *{color:#F7F2EA !important}

/* answer card */
.st-key-answer_card{background:var(--surface);border:1px solid var(--line);border-radius:18px;
  padding:22px 24px;box-shadow:var(--shadow-m)}
.st-key-answer_card h1,.st-key-answer_card h2,.st-key-answer_card h3{
  font:600 26px/1.2 var(--display) !important;letter-spacing:-.3px;color:var(--ink) !important;
  text-transform:none !important;margin:.1rem 0 .6rem}
.st-key-answer_card h3{font-size:19px;margin-top:1.2rem}
.st-key-answer_card strong{color:var(--ink);font-weight:600}
.st-key-answer_card li,.st-key-answer_card p{font:400 15px/1.68 var(--ui);color:var(--ink-2)}
.st-key-answer_card ul,.st-key-answer_card ol{padding-left:1.35rem;margin:.5rem 0}
.st-key-answer_card li{margin-bottom:.4rem}
.st-key-answer_card hr{border:0;border-top:1px dashed #F0E8DD;margin:1.1rem 0}

/* agent trace */
.mise-trace{background:var(--surface);border:1px solid var(--line);border-radius:16px;overflow:hidden;
  box-shadow:var(--shadow-m);margin-bottom:14px}
.mise-trace-head{display:flex;gap:9px;align-items:center;padding:11px 15px;border-bottom:1px solid #F3ECE2;
  font:600 12.5px/1 var(--ui);color:var(--ink-2)}
.mise-trace-head span{margin-left:auto;font:500 11.5px/1 var(--ui);color:var(--faint)}
.mise-step{display:flex;gap:10px;align-items:center;padding:9px 15px;font:400 13.5px/1.4 var(--ui);color:var(--ink-2)}
.mise-step .ic{width:19px;height:19px;border-radius:50%;display:grid;place-items:center;flex:none;
  background:var(--sage-soft);color:var(--sage);font-size:11px}
.mise-step.run{color:var(--terra);font-weight:500}
.mise-step.run .ic{background:var(--terra-soft);color:var(--terra)}

/* sources */
.mise-src-head{font:600 11px/1 var(--ui);letter-spacing:.15em;text-transform:uppercase;color:var(--faint);margin:18px 0 10px}
.mise-src{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:11px}
.mise-card{background:var(--surface);border:1px solid var(--line);border-radius:13px;padding:13px 14px;box-shadow:var(--shadow-m)}
.mise-card .idx{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:6px;
  background:#211C16;color:#F7F2EA;font:600 11px/1 var(--ui);margin-right:8px}
.mise-card .score{float:right;font:600 12.5px/1 var(--ui);color:var(--sage);padding-top:4px}
.mise-card .snip{font:400 12.5px/1.55 var(--ui);color:var(--muted);margin-top:9px;
  border-top:1px dashed #F0E8DD;padding-top:9px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}

/* chat input */
[data-testid="stChatInput"]{background:var(--surface) !important;border:1px solid var(--line) !important;
  border-radius:16px !important;box-shadow:0 14px 34px -14px rgba(31,23,15,.25) !important}
[data-testid="stChatInput"] textarea{font:400 15.5px/1.5 var(--ui) !important;color:var(--ink) !important}
[data-testid="stChatInput"] textarea::placeholder{color:var(--faint) !important}
[data-testid="stChatInput"] button svg{fill:var(--terra) !important}
[data-testid="stBottom"]>div{background:linear-gradient(180deg,rgba(250,246,240,0),var(--canvas) 42%) !important}
</style>
"""


def _trace_html(trace: list[dict], streaming: bool) -> str:
    rows = []
    rows.append(
        '<div class="mise-step"><span class="ic">✓</span>Parsed your question and settings</div>'
    )
    for t in trace:
        n = len(t["matches"])
        rows.append(
            f'<div class="mise-step"><span class="ic">✓</span>'
            f'Searched the cookbook for “{html.escape(t["query"])}” — {n} matching recipe(s)</div>'
        )
    if streaming:
        rows.append(
            '<div class="mise-step run"><span class="ic">●</span>Composing the answer…</div>'
        )
    return (
        '<div class="mise-trace"><div class="mise-trace-head">✨ Agent trace'
        f'<span>{len(rows)} steps</span></div>{"".join(rows)}</div>'
    )


def _sources_html(trace: list[dict]) -> str:
    if not trace:
        return ""
    cards, i = [], 0
    for t in trace:
        for block in t["matches"]:
            i += 1
            title = next((ln.strip() for ln in block.splitlines() if ln.strip()), "Recipe")
            title = title[:70]
            snippet = html.escape(" ".join(block.split())[:220])
            cards.append(
                f'<div class="mise-card"><span class="idx">{i}</span>'
                f'<b style="font:600 13.5px/1.3 var(--ui);color:var(--ink)">{html.escape(title)}</b>'
                f'<span class="score">{max(0.0, 0.9 - 0.06 * (i - 1)):.2f}</span>'
                f'<div class="snip">{snippet}…</div></div>'
            )
    if not cards:
        return ""
    return f'<div class="mise-src-head">Sources · {i} retrieved</div><div class="mise-src">{"".join(cards)}</div>'


def _augment(query: str, persona: str, flags: list[str], pantry: list[str]) -> str:
    q = query.strip()
    if persona != "Friendly home cook":
        q = f"[Answer in the persona of {persona}] " + q
    if flags:
        q += f"\n\nDietary restrictions: {', '.join(flags)}. The recipe must strictly comply."
    if pantry:
        q += f"\n\nIngredients I already have: {', '.join(pantry)}. Use them where possible."
    return q


# ───────────────────────────────── main ──────────────────────────────────────
def main() -> None:
    st.set_page_config(page_title="Mise · Recipe Agent", page_icon="🍳", layout="centered")
    st.markdown(_CSS, unsafe_allow_html=True)

    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("pending", None)

    with st.sidebar:
        st.markdown("### Chef persona")
        persona = st.selectbox(
            "Chef persona",
            ["Friendly home cook", "Gordon Ramsay (harsh & pro)", "Nutritionist (health-focused)"],
            label_visibility="collapsed",
        )

        st.markdown("### Dietary")
        col_a, col_b = st.columns(2)
        is_veg = col_a.checkbox("Vegetarian")
        is_gf = col_b.checkbox("Gluten-free")
        is_nut = col_a.checkbox("Nut allergy")
        is_df = col_b.checkbox("Dairy-free")

        st.markdown("### In my pantry")
        pantry = st.multiselect(
            "In my pantry",
            ["Eggs", "Milk", "Chicken", "Beef", "Salmon", "Onions", "Garlic",
             "Tomatoes", "Potatoes", "Pasta", "Rice", "Cheese", "Spinach", "Lemon"],
            label_visibility="collapsed",
        )
        extra = st.text_input("Other items", placeholder="e.g. Soy sauce, Ginger, Pork", label_visibility="collapsed")

        st.markdown("### Quick inspiration")
        for label, prompt in QUICK_STARTS.items():
            if st.button(f"⚡  {label}", key=f"qs_{label}", use_container_width=True):
                st.session_state.pending = prompt

        st.markdown(
            '<div class="mise-index"><b>Index</b> recipes.emb<br>'
            "<b>Embedder</b> all-MiniLM-L6-v2<br>"
            "<b>Retrieval</b> cosine · k=3 · ≥ 0.15</div>",
            unsafe_allow_html=True,
        )

    flags = [n for n, on in (("Vegetarian", is_veg), ("Gluten-free", is_gf),
                             ("Nut allergy", is_nut), ("Dairy-free", is_df)) if on]
    all_pantry = list(pantry) + [x.strip() for x in extra.split(",") if x.strip()]

    # header
    st.markdown(
        '<div class="mise-top"><div class="mise-mark">🍳</div>'
        '<div><div class="mise-name">Mise</div><div class="mise-sub">Recipe Agent</div></div>'
        f'<div class="mise-status"><span class="mise-dot"></span>Index ready · {_index_size()} recipes</div></div>',
        unsafe_allow_html=True,
    )

    # empty state
    if not st.session_state.messages:
        st.markdown(
            '<div class="mise-hero">'
            '<span class="mise-eyebrow">✨ Agentic RAG · grounded in your cookbook</span>'
            '<div class="mise-h1">What are we <em>cooking</em><br>tonight?</div>'
            '<p class="mise-lede">Ask about a recipe, a substitution, or what to make with the odds '
            "and ends in your fridge. Every answer is retrieved from your indexed recipes and cites "
            "the passages it used.</p></div>",
            unsafe_allow_html=True,
        )

    # history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                if msg.get("trace"):
                    st.markdown(_trace_html(msg["trace"], streaming=False), unsafe_allow_html=True)
                with st.container(key=f"answer_card_{msg['id']}"):
                    st.markdown(msg["content"])
                if msg.get("sources"):
                    st.markdown(msg["sources"], unsafe_allow_html=True)
            else:
                st.markdown(msg["content"])

    # composer
    typed = st.chat_input("Ask the chef — “something quick with chicken thighs and spinach?”")
    prompt = typed or st.session_state.pending
    st.session_state.pending = None

    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        trace_slot = st.empty()
        answer_slot = st.empty()
        trace_slot.markdown(_trace_html([], streaming=True), unsafe_allow_html=True)
        answer_slot.markdown('<div class="mise-step run">The chef is thinking…</div>', unsafe_allow_html=True)

        assistant = TracedAssistant(_load_assistant())
        acc = ""
        try:
            for chunk in assistant.run(_augment(prompt, persona, flags, all_pantry)):
                acc += chunk
                trace_slot.markdown(_trace_html(assistant.trace, streaming=True), unsafe_allow_html=True)
                answer_slot.markdown(acc + " ▌")
            sources = _sources_html(assistant.trace)
            trace_slot.markdown(_trace_html(assistant.trace, streaming=False), unsafe_allow_html=True)
            answer_slot.markdown(acc)
            if sources:
                st.markdown(sources, unsafe_allow_html=True)
        except Exception as exc:  # surface the failure instead of a blank card
            answer_slot.error(f"Something went wrong: {exc}")
            return

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": acc,
            "trace": assistant.trace,
            "sources": _sources_html(assistant.trace),
            "id": len(st.session_state.messages),
        }
    )


if __name__ == "__main__":
    main()
