# RecipeRAG: An Agentic Culinary Assistant

## 📖 Overview

RecipeRAG is an intelligent, Agentic RAG (Retrieval-Augmented Generation) application designed for recipe retrieval, culinary queries, and ingredient scaling. Unlike traditional single-pass RAG pipelines, RecipeRAG utilizes an LLM-driven router to classify user intents dynamically, apply semantic guardrails, and generate formatted, context-aware culinary advice. 

The application is deployed with a modern, dark-themed Glassmorphism UI via Streamlit and is fully configured for Streamlit Cloud deployment.

---

## ✨ Core Features

*   **Autonomous Agentic Execution (`app.py` & `llm.py`)**: Fully deprecated static `if/else` routing. Utilizes native LLM Tool Calling (Function Calling) within an autonomous ReAct loop. The Agent decides when to search the cookbook, calculate ingredient scaling, or directly answer questions.
*   **Semantic Guardrails (`prompting.py`)**: Uses a strict system prompt to intercept off-topic queries (e.g., politics, coding), preventing out-of-domain hallucinations.
*   **Vector Search**: Utilizes `sentence-transformers` (`all-MiniLM-L6-v2`) with cosine similarity scoring, exposed directly to the LLM as a `search_cookbook` tool.
*   **Streamlit Cloud Ready**: Zero-config deployment bridging local `.env` variables with `st.secrets`.

---

## 🧪 Evaluation & Metrics

The RAG pipeline is evaluated via an automated test suite. If an API rate limit (`429 Too Many Requests`) occurs during testing, that query is cleanly skipped from the final averages.

Run the evaluation:
```bash
python scripts/rag_evaluator.py
```

### 1. LLM-as-a-Judge (Semantic Accuracy: 0-10)
Instead of rigid string matching, an evaluator LLM scores the generated answer against the ground truth based on **Faithfulness** (no hallucinations) and **Completeness**. High scores indicate correct, human-like summarization.

### 2. ROUGE-L (Lexical Overlap)
Measures exact structural string matching (Longest Common Subsequence). In Agentic RAG, ROUGE-L is a secondary metric; a high LLM score paired with a moderate ROUGE-L score indicates the Agent is successfully synthesizing information rather than blindly copy-pasting.

### 3. System Latency
End-to-end execution time. Simple responses take ~1-2s, while autonomous Tool Calling (ReAct loops) naturally take 10-15s to complete the full "Think $\rightarrow$ Search $\rightarrow$ Answer" cycle.

### Sample Output
```text
📊 Evaluation Summary
==================================================
Total Queries Evaluated : 2
Total Queries Skipped   : 3
Average LLM Judge Score : 8.00 / 10.0 (Semantic Accuracy)
Average System Latency  : 12.88 seconds/query
==================================================
```

---

## 🚀 Quickstart

1.  **Environment Setup:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **API Configuration:**
    Create a `.env` file in the root directory:
    ```env
    OPENAI_API=your_api_key_here
    OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
    OPENAI_MODEL=meta/llama-3.1-70b-instruct
    ```
3.  **Launch the UI:**
    ```bash
    streamlit run streamlit_app.py
    ```
