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
import random
import threading
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI, HTTPException, Query
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


#: Set WARMUP=0 to skip the one-token model call made at boot.
WARMUP_ENABLED = os.getenv("WARMUP", "1").strip().lower() not in {"0", "false", "no"}

_warm_state: dict[str, Any] = {"llm_ok": None, "llm_ms": None, "error": None, "at": None}


def _touch_llm() -> tuple[bool, int, str]:
    """Make the cheapest possible call to the chat model.

    Two things get paid for here instead of on the user's first question: the
    DNS + TLS + connection setup to the provider, and finding out early that the
    key or model name is wrong. It does *not* reduce the provider's queueing
    delay — that is remote and out of our hands.
    """
    assistant = get_assistant()
    started = time.perf_counter()
    try:
        reply = assistant.llm.chat("Reply with the single word: ready", max_tokens=24)
        # An empty reply is still a successful round trip: the connection is warm
        # and the credentials were accepted. Reasoning models routinely spend a
        # small budget on deliberation and return no visible text, so this is
        # reported as a note, never as an error.
        note = "" if reply else "empty reply (normal for reasoning models)"
        return True, int((time.perf_counter() - started) * 1000), note
    except Exception as exc:
        return False, int((time.perf_counter() - started) * 1000), str(exc)[:300]


def _warm_llm_in_background() -> None:
    """Run the warm-up off the startup path.

    Awaiting it in lifespan would delay the port binding, and Render's health
    check would then see a slower boot than necessary.
    """
    ok, ms, err = _touch_llm()
    _warm_state.update(llm_ok=ok, llm_ms=ms, error=err or None, at=time.time())
    if ok:
        print(f"[warmup] chat model responded in {ms} ms", flush=True)
    else:
        print(f"[warmup] chat model FAILED after {ms} ms: {err}", flush=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Blocking part: the embedding model and index. The service is not really up
    # until this succeeds, so /healthz has to reflect it.
    try:
        get_assistant()
        print("[startup] index and embedder ready", flush=True)
    except Exception as exc:  # stay up so /healthz can report the problem
        print(f"[startup] assistant failed to load: {exc}", flush=True)

    if WARMUP_ENABLED:
        threading.Thread(target=_warm_llm_in_background, name="warmup", daemon=True).start()
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
                # TheMealDB thumbnails; the UI shows them as a hero image and
                # as source-card previews. 788/829 recipes have one.
                "image": (h.metadata or {}).get("image", ""),
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
        # null while the background warm-up is still in flight
        "llm_warm": _warm_state["llm_ok"],
    }


@app.get("/api/index")
def index_info() -> dict[str, Any]:
    assistant = get_assistant()
    return {
        **assistant.index_meta,
        "k": assistant.k,
        "min_similarity": assistant.min_similarity,
    }


@app.get("/warmup")
def warmup() -> dict[str, Any]:
    """Force a full warm-up. Hit this shortly before demoing.

    On a free instance the container is evicted after ~15 minutes idle, so the
    next request pays the whole boot. Calling this from a browser tab, a cron
    job or an uptime pinger means that cost lands on nobody's first impression.
    """
    started = time.perf_counter()
    try:
        assistant = get_assistant()
    except Exception as exc:
        return {"ready": False, "error": str(exc)}

    index_ms = int((time.perf_counter() - started) * 1000)
    ok, llm_ms, err = _touch_llm()
    _warm_state.update(llm_ok=ok, llm_ms=llm_ms, error=err or None, at=time.time())

    return {
        "ready": ok,
        "index_ms": index_ms,
        "llm_ok": ok,
        "llm_ms": llm_ms,
        "model": assistant.llm.model,
        "recipes": assistant.index_meta.get("count"),
        "note": err or None,
    }


@app.get("/api/recipes")
def list_recipes(
    q: str = "",
    category: str = "",
    area: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=60),
) -> dict[str, Any]:
    """Browse or search the cookbook directly.

    Deliberately does not touch the LLM: searching 829 embeddings takes about a
    millisecond, so this entry point stays usable when the model is queued,
    rate-limited or out of quota. The agentic chat is unchanged — this is an
    additional way in, not a replacement.
    """
    assistant = get_assistant()
    entries = assistant.vector_store

    # filter first, so scoring and paging only see the candidates
    rows = list(enumerate(entries))
    if category:
        rows = [(i, e) for i, e in rows if (e.get("metadata") or {}).get("category") == category]
    if area:
        rows = [(i, e) for i, e in rows if (e.get("metadata") or {}).get("area") == area]

    query = q.strip()
    scored: list[tuple[float, int, dict[str, Any]]] = []
    if query:
        from recipe_rag.retrieval import _cosine_scores, _coerce_embedding

        vec = _coerce_embedding(assistant.embedder.encode(query))
        matrix = assistant.matrix[[i for i, _ in rows]] if rows else None
        sims = _cosine_scores(vec, matrix) if matrix is not None else []
        scored = [(float(s), i, e) for (i, e), s in zip(rows, sims)]
        scored.sort(key=lambda t: -t[0])
    else:
        scored = [(0.0, i, e) for i, e in sorted(rows, key=lambda t: (t[1].get("metadata") or {}).get("title", ""))]

    total = len(scored)
    start = (page - 1) * page_size
    window = scored[start : start + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": start + page_size < total,
        "query": query,
        "items": [
            {
                "id": idx,
                "title": (e.get("metadata") or {}).get("title", ""),
                "image": (e.get("metadata") or {}).get("image", ""),
                "category": (e.get("metadata") or {}).get("category", ""),
                "area": (e.get("metadata") or {}).get("area", ""),
                "score": round(score, 4) if query else None,
            }
            for score, idx, e in window
        ],
        "facets": _facets(),
    }


@lru_cache(maxsize=1)
def _facets() -> dict[str, list[dict[str, Any]]]:
    assistant = get_assistant()
    counts: dict[str, dict[str, int]] = {"category": {}, "area": {}}
    for entry in assistant.vector_store:
        meta = entry.get("metadata") or {}
        for key in ("category", "area"):
            value = (meta.get(key) or "").strip()
            if value:
                counts[key][value] = counts[key].get(value, 0) + 1
    return {
        key: [{"value": v, "count": c} for v, c in sorted(counts[key].items(), key=lambda kv: -kv[1])]
        for key in counts
    }


@app.get("/api/recipes/{rid}")
def recipe_detail(rid: int) -> dict[str, Any]:
    """The full text of one recipe, for the browse detail panel."""
    assistant = get_assistant()
    if rid < 0 or rid >= len(assistant.vector_store):
        raise HTTPException(status_code=404, detail="No such recipe")
    meta = assistant.vector_store[rid].get("metadata") or {}
    return {
        "id": rid,
        "title": meta.get("title", ""),
        "image": meta.get("image", ""),
        "category": meta.get("category", ""),
        "area": meta.get("area", ""),
        "ingredients": meta.get("ingredients", ""),
        "instructions": meta.get("instructions", ""),
        "notes": meta.get("notes", ""),
        "serving_size": meta.get("serving_size"),
    }


@app.get("/api/recipes/sample")
def sample_recipes(n: int = Query(6, ge=1, le=12)) -> list[dict[str, Any]]:
    """A few random dishes for the empty state.

    The corpus carries a photo for 788 of its 829 recipes; showing a handful
    before the user has asked anything makes the library visible instead of
    implied.
    """
    assistant = get_assistant()
    pool = [e for e in assistant.vector_store if (e.get("metadata") or {}).get("image")]
    if not pool:
        return []
    picked = random.sample(pool, min(n, len(pool)))
    return [
        {
            "title": (e.get("metadata") or {}).get("title", ""),
            "image": (e.get("metadata") or {}).get("image", ""),
            "category": (e.get("metadata") or {}).get("category", ""),
            "area": (e.get("metadata") or {}).get("area", ""),
        }
        for e in picked
    ]


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
