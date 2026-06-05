# RecipeRAG: An Agentic Culinary Assistant

## 📖 Overview

RecipeRAG is an intelligent, Agentic RAG (Retrieval-Augmented Generation) application designed for recipe retrieval, culinary queries, and ingredient scaling. Unlike traditional single-pass RAG pipelines, RecipeRAG utilizes an LLM-driven router to classify user intents dynamically, apply semantic guardrails, and generate formatted, context-aware culinary advice. 

The application is deployed with a modern, dark-themed Glassmorphism UI via Streamlit and is fully configured for Streamlit Cloud deployment.

---

## ✨ Core Features

*   **Agentic Intent Routing (`router.py`)**: Uses a zero-shot LLM classifier to determine the execution path before retrieval. Distinct pipelines handle `SearchRecipeIntent`, `ScaleRecipeIntent`, `CookingQuestionIntent`, and `OtherIntent`.
*   **Semantic Guardrails & Relevance Filtering (`relevance.py`)**: Implements strict `is_cookbook_relevant` and `is_cooking_related` checks. This actively intercepts off-topic queries, preventing jailbreaks and out-of-domain hallucinations without wasting retrieval compute.
*   **Vector Search & Dimensionality Reduction**: Utilizes `sentence-transformers` (`all-MiniLM-L6-v2`) with cosine similarity scoring. Includes a built-in t-SNE module (`visualize_embeddings.py`) to project the high-dimensional recipe space into 2D for exploratory data analysis (EDA).
*   **Streamlit Cloud Ready**: Uses a custom hydration script to automatically sync local `.env` variables with `st.secrets`, enabling zero-config cloud deployments.

---

## 🧪 Evaluation Methodology & Metrics

To ensure production-level reliability, the RAG pipeline is evaluated using a hybrid framework combining modern LLM-based evaluation with traditional NLP syntactic metrics. 

Run the automated evaluation pipeline via:
```bash
python scripts/rag_evaluator.py
```

### 1. LLM-as-a-Judge (Semantic & Factual Accuracy)
Given the generative nature of RAG, traditional exact-match metrics often falsely penalize correct but paraphrased answers. We utilize an **LLM-as-a-Judge** paradigm. 
*   **Scoring (0.0 - 10.0)**: A designated evaluator LLM compares the **Generated Answer** against a predefined **Ground Truth Reference**.
*   **Evaluation Criteria**:
    *   **Faithfulness**: Absence of hallucinations. All generated claims must be strictly grounded in the retrieved vector context.
    *   **Context Recall (Completeness)**: The extent to which the generated answer extracts all necessary information from the retrieved context to fully satisfy the query.
    *   **Answer Relevance**: Precision in directly addressing the user's prompt without introducing tangentially related noise.

### 2. ROUGE-L (Lexical Overlap)
*   Computes the **Longest Common Subsequence (LCS)** between the generated text and the ground truth. 
*   *Note: In Agentic RAG architectures, ROUGE-L serves primarily as a secondary proxy metric. High semantic accuracy (via LLM Judge) paired with a low ROUGE-L score typically indicates successful, high-quality paraphrasing/summarization by the generation node.*

### 3. End-to-End Latency
*   Quantifies the round-trip execution time in seconds, encompassing Intent Classification (Routing) $\rightarrow$ Dense Vector Retrieval $\rightarrow$ Context Injection $\rightarrow$ Generation.

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