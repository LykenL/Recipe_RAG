import streamlit as st
from recipe_rag.app import RecipeRAGAssistant
from pathlib import Path

st.set_page_config(page_title="Recipe RAG Demo", layout="centered")

st.title("🧑‍🍳 Recipe Retrieval‑Augmented Generation")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    vector_path = st.text_input("Vector store path", value=str(Path.cwd() / "vector_store"))
    embedding_model = st.selectbox("Embedding model", ["all-MiniLM-L6-v2", "paraphrase-MiniLM-L6-v2"])
    dotenv_path = st.text_input(".env path (optional)")
    if st.button("Load Assistant"):
        try:
            st.session_state.assistant = RecipeRAGAssistant.from_files(
                vector_store_path=vector_path,
                dotenv_path=dotenv_path or None,
                embedding_model=embedding_model,
            )
            st.success("Assistant loaded!")
        except Exception as e:
            st.error(f"Failed to load: {e}")

if "assistant" not in st.session_state:
    st.info("Load the assistant from the sidebar to begin.")
    st.stop()

# Main interaction
query = st.text_area("Ask a cooking question or search a recipe", height=150)
if st.button("Submit"):
    with st.spinner("Thinking…"):
        try:
            response = st.session_state.assistant.route(query)
            from recipe_rag.formatting import normalize_answer_lines

            st.markdown(normalize_answer_lines(response))
        except Exception as e:
            st.error(f"Error: {e}")
