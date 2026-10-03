"""
Recipe RAG API — FastAPI + Server-Sent Events.

Endpoints
---------
  GET  /healthz         liveness probe for Render
  GET  /api/index       index metadata (count, model, dimension)
  POST /api/chat        SSE stream: trace -> sources -> token* -> done

Why SSE and not plain JSON: the whole point of moving off Streamlit is being
able to show the agent working — retrieval steps, then tokens, then citations.
A single POST response cannot express that.

Concurrency note
----------------
`RecipeRAGAssistant` is a process-wide singleton (the embedding model is the
expensive part and must be loaded once). `search_cookbook` is patched per
request to record hits, so each request works on a shallow copy of the
assistant — see `_view()`. Without that, two overlapping requests would
overwrite each other's retrieved sources.
"""

from __future__ import annotations

import copy
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = Path(os.getenv("INDEX_PATH") or ROOT / "artifacts" / "index")

_assistant: Any = None


def get_assistant():
    """Load once, reuse forever. Model load is the dominant cold-start cost."""
    global _assistant
    if _assistant is None:
        from recipe_rag.app import RecipeRAGAssistant

        vector_path = INDEX_PATH
        if not vector_path.exists():
            # fall back to the legacy pickle next to it
            legacy = ROOT / "artifacts" / "recipes.emb"
            if legacy.is_file():
                vector_path = legacy
            else:
                raise RuntimeError(f"No index found at {INDEX_PATH} (run scripts/build_index.py)")

        _assistant = RecipeRAGAssistant.from_files(vector_store_path=vector_path)
    return _assistant


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warm the model at boot so the first user request is not the one paying for it.
    try:
        get_assistant()
    except Exception as exc:  # keep the service up so /healthz can report the problem
        print(f"[startup] assistant failed to load: {exc}", flush=True)
    yield


app = FastAPI(title="Recipe RAG API", version="1.0", lifespan=lifespan)

_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── request/response models ──────────────────────────────────────────────────
class Turn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[Turn] = Field(default_factory=list)
    persona: str = "Friendly home cook"
    dietary: list[str] = Field(default_factory=list)
    pantry: list[str] = Field(default_factory=list)
    conversation_id: str | None = None


def _augment(req: ChatRequest) -> str:
    """Fold the sidebar settings into the prompt, exactly like the Streamlit app did."""
    query = req.message.strip()
    if req.persona and req.persona != "Friendly home cook":
        query = f"[Answer in the persona of {req.persona}] " + query
    if req.dietary:
        query += f"\n\nDietary restrictions: {', '.join(req.dietary)}. The recipe must strictly comply."
    if req.pantry:
        query += f"\n\nIngredients I already have: {', '.join(req.pantry)}. Use them where possible."
    return query


# ── SSE plumbing ─────────────────────────────────────────────────────────────
def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _view(assistant: Any, trace: list[dict[str, Any]]):
    """Shallow copy so per-request bookkeeping never leaks between requests."""
    view = copy.copy(assistant)
    original = assistant.search_cookbook

    def traced_search(query: str) -> str:
        started = time.perf_counter()
        text = original(query)
        hits = [
            {
                "title": h.title,
                "score": round(float(h.score), 4),
                "snippet": h.snippet,
                "full_text": h.full_text[:6000],
                "source": h.source,
                "category": (h.metadata or {}).get("category", ""),
                "area": (h.metadata or {}).get("area", ""),
            }
            for h in getattr(assistant, "last_hits", [])
        ]
        trace.append(
            {
                "step": "search",
                "query": query,
                "hits": len(hits),
                "sources": hits,
                "ms": int((time.perf_counter() - started) * 1000),
            }
        )
        return text

    view.search_cookbook = traced_search  # instance attribute; isolated to this copy
    return view


def event_stream(req: ChatRequest) -> Iterator[str]:
    started = time.perf_counter()
    try:
        assistant = get_assistant()
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})
        return

    trace: list[dict[str, Any]] = []
    view = _view(assistant, trace)

    yield _sse(
        "trace",
        {
            "step": "parse",
            "label": "Parsed your question and kitchen settings",
            "ms": int((time.perf_counter() - started) * 1000),
        },
    )

    history = [t.model_dump() for t in req.history]
    emitted = 0
    answer = ""

    try:
        for chunk in view.run(_augment(req), history=history):
            answer += chunk
            # tool calls happen between chunks; surface new ones as they land
            while emitted < len(trace):
                entry = trace[emitted]
                emitted += 1
                yield _sse("trace", entry)
                if entry.get("sources"):
                    yield _sse("sources", entry["sources"])
            yield _sse("token", {"t": chunk})
    except Exception as exc:
        yield _sse("error", {"message": f"{type(exc).__name__}: {exc}"})
        return

    while emitted < len(trace):
        entry = trace[emitted]
        emitted += 1
        yield _sse("trace", entry)
        if entry.get("sources"):
            yield _sse("sources", entry["sources"])

    # Report the sources from the final search — that is what the answer actually
    # rests on. (The agent may probe several times; summing them would inflate
    # the citation count and mislead the reader.)
    searches = [t for t in trace if t.get("step") == "search"]
    latest_sources = searches[-1]["sources"] if searches else []

    yield _sse(
        "done",
        {
            "answer": answer,
            "citations": len(latest_sources),
            "searches": len(searches),
            "index": assistant.index_meta.get("count"),
            "model": assistant.index_meta.get("model"),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        },
    )


# ── routes ───────────────────────────────────────────────────────────────────
@app.get("/healthz")
def healthz() -> dict[str, Any]:
    try:
        assistant = get_assistant()
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)}
    return {
        "status": "ok",
        "recipes": assistant.index_meta.get("count"),
        "model": assistant.index_meta.get("model"),
        "backend": assistant.index_meta.get("backend"),
    }


@app.get("/api/index")
def index_info() -> dict[str, Any]:
    assistant = get_assistant()
    return {
        **assistant.index_meta,
        "k": assistant.k,
        "min_similarity": assistant.min_similarity,
    }


@app.post("/api/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        event_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # stops nginx-style proxies (and some PaaS routers) buffering the stream
            "X-Accel-Buffering": "no",
        },
    )


# ── optional: serve the built React app from the same service ────────────────
# One service, no CORS, no separate Static Site. Enable by building the frontend
# into apps/web/dist before deploying.
_web_dist = Path(os.getenv("WEB_DIST") or ROOT / "apps" / "web" / "dist")
if _web_dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_web_dist), html=True), name="web")
