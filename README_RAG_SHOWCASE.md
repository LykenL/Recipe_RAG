# Recipe RAG Assistant (Showcase)

This folder contains a small, job-ready packaging of the original lab notebooks (Lab2–Lab4): embeddings + vector search + RAG prompting + intent routing.

## Quick start

1) Install dependencies:

```bash
pip install -r requirements.txt
```

2) Create `.env` (see `.env.example`) and set:
- `OPENAI_API` (or `OPENAI_API_KEY`)
- (optional) `OPENAI_BASE_URL`
- (optional) `OPENAI_MODEL`

## Deploy the web UI (share a public link)

```bash
streamlit run streamlit_app.py
```

See **[DEPLOY.md](DEPLOY.md)** for Streamlit Community Cloud (GitHub + Secrets).

3) Run retrieval-only sanity check:

```bash
python3 scripts/eval_queries.py --vector-store week_3/COLX_563_lab3_Lyken35/recipes.emb
```

4) Run the CLI (RAG answer):

```bash
python3 -m recipe_rag.cli --vector-store week_3/COLX_563_lab3_Lyken35/recipes.emb ask "strawberry pie"
```

## Build your own index

```bash
python3 scripts/build_index.py --recipes week_2/COLX_563_lab2_Lyken35/lab1_recipes_f.json --out artifacts/recipes.emb
```

