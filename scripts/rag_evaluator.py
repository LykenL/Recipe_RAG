# scripts/rag_evaluator.py
from __future__ import annotations

import sys
import time
import re
from pathlib import Path

# 把项目根目录加入到 Python 环境变量，避免 ModuleNotFoundError
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Try importing standard NLP metrics, fallback to None if not installed
try:
    from rouge_score import rouge_scorer
    SCORER = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
except ImportError:
    SCORER = None

from recipe_rag.app import RecipeRAGAssistant
from recipe_rag.config import load_env

# ── 1. 定义测试数据集 (Ground Truth) ─────────────────────────────────────────
EVAL_DATASET = [
    {
        "query": "What are the main ingredients for a strawberry pie?",
        "reference": "The main ingredients are typically fresh strawberries, sugar, water, cornstarch, and pie crust.",
    },
    {
        "query": "How long should I bake a standard casserole?",
        "reference": "Based on the cookbook, casseroles are typically baked for 15 to 25 minutes at 450°F or 350°F until cooked through.",
    },
    {
        "query": "What are the notes for tuna broccoli casserole?",
        "reference": "Broccoli right in your biscuits!",
    },
    {
        "query": "What can I cook with pineapple?",
        "reference": "You can make Pineapple Sticky Buns, Waffles with Pineapple, or Pineapple Coffee Cake.",
    },
    {
        "query": "If a recipe serves 4, how do I scale the ingredients to serve 8?",
        "reference": "To scale a recipe from 4 servings to 8 servings, you simply need to double (multiply by 2) all the ingredient quantities.",
    },
]


# ── 2. 定义 LLM 裁判 (LLM-as-a-Judge) ───────────────────────────────────────
def evaluate_with_llm(assistant: RecipeRAGAssistant, question: str, generated: str, reference: str) -> float | None:
    """使用 LLM 作为裁判，对答案的准确性进行 0-10 的打分。"""
    prompt = f"""
You are an expert evaluator for a Recipe RAG system.
Please evaluate the GENERATED ANSWER against the REFERENCE ANSWER for the given QUESTION.
Score the GENERATED ANSWER from 0 to 10 based on factual accuracy, completeness, and lack of hallucination.

QUESTION: {question}
REFERENCE ANSWER: {reference}
GENERATED ANSWER: {generated}

Output ONLY a valid JSON object in the following format, with no extra text or markdown wrappers:
{{"score": 8}}
"""
    try:
        response = assistant.llm.chat(prompt, max_tokens=15)
    except Exception as e:
        print(f"   [!] Judge API Error: {e}")
        return None

    try:
        import json
        data = json.loads(response.strip().strip('`').strip('json'))
        return float(data.get("score", 0.0))
    except Exception:
        # Fallback to regex if JSON fails
        import re
        match = re.search(r"\b([0-9]|10)(?:\.0)?\b", response)
        if match:
            return float(match.group(1))
        print(f"   [!] Judge Parsing Error, returning 0.0")
        return 0.0


# ── 3. 主评测逻辑 ────────────────────────────────────────────────────────────
def compute_rouge(generated: str, reference: str) -> float:
    if SCORER:
        return SCORER.score(reference, generated)["rougeL"].fmeasure
    return 0.0

def main():
    root = Path(__file__).parent.parent
    load_env(root / ".env")
    
    # 自动寻找向量库路径
    vector_store_candidates = [
        root / "artifacts" / "recipes.emb",
        root / "week_3" / "COLX_563_lab3_Lyken35" / "recipes.emb"
    ]
    vector_store_path = next((p for p in vector_store_candidates if p.exists()), None)
    
    if not vector_store_path:
        print("❌ Error: Could not find recipes.emb vector store.")
        return

    print("🚀 [1/3] Loading Recipe RAG Assistant...")
    assistant = RecipeRAGAssistant.from_files(
        vector_store_path=vector_store_path,
        dotenv_path=None,
        embedding_model="all-MiniLM-L6-v2",
    )
    
    print(f"✅ Loaded! Using LLM: {assistant.llm.model}")
    print("⏳ [2/3] Starting Evaluation Pipeline (LLM-as-a-Judge + ROUGE-L)...\n")

    scores = []
    rouge_scores = []
    latencies = []
    skipped = 0

    for i, item in enumerate(EVAL_DATASET, 1):
        query = item["query"]
        ref = item["reference"]
        print(f"▶️  Testing Query {i}/{len(EVAL_DATASET)}: {query}")

        start = time.time()
        try:
            generated = assistant.route(query)
            latency = time.time() - start
        except Exception as e:
            print(f"   [!] Generation API Error (Skipping): {e}")
            skipped += 1
            print()
            continue

        llm_score = evaluate_with_llm(assistant, query, generated, ref)
        if llm_score is None:
            skipped += 1
            print()
            continue

        rouge_l = compute_rouge(generated, ref)

        scores.append(llm_score)
        rouge_scores.append(rouge_l)
        latencies.append(latency)

        print(f"   ↳ LLM Judge Score : {llm_score:.1f}/10.0")
        if SCORER:
            print(f"   ↳ ROUGE-L Score   : {rouge_l:.3f}")
        print(f"   ↳ Latency         : {latency:.2f}s\n")

    # ── 4. 输出汇总报告 ──────────────────────────────────────────────────────────
    print("📊 [3/3] Evaluation Summary")
    print("=" * 50)
    print(f"Total Queries Evaluated : {len(scores)}")
    print(f"Total Queries Skipped   : {skipped}")
    
    if scores:
        avg_score = sum(scores) / len(scores)
        avg_rouge = sum(rouge_scores) / len(rouge_scores)
        avg_latency = sum(latencies) / len(latencies)

        print(f"Average LLM Judge Score : {avg_score:.2f} / 10.0 (Semantic Accuracy)")
        if SCORER:
            print(f"Average ROUGE-L Score   : {avg_rouge:.3f} (Lexical Overlap)")
        print(f"Average System Latency  : {avg_latency:.2f} seconds/query")
        print("=" * 50)

        if avg_score >= 8.0:
            print("🌟 Excellent Performance! System is highly accurate.")
        elif avg_score >= 6.0:
            print("👍 Good Performance, but some edge cases might need better context retrieval.")
        else:
            print("⚠️ Suboptimal Performance. Consider tuning chunk sizes, Top-K, or the prompt.")
    else:
        print("No valid queries were evaluated due to API errors.")
        print("=" * 50)


if __name__ == "__main__":
    main()
