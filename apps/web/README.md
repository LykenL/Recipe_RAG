# apps/web — Mise frontend

React 19 + Vite 6 + TypeScript. No CSS framework: the design tokens live in
`src/styles.css` and are a direct port of `recipe_rag/redesign/mockup-react.html`,
so the built app matches the approved mockup.

## Run against the API

The API must be running first (see `DEPLOY_API.md`):

```bash
# terminal 1 — backend on :8000
cd ../..            # repo root
PYTHONPATH=. .venv/bin/uvicorn services.api.main:app --port 8000

# terminal 2 — frontend on :5173
cd apps/web
npm install
npm run dev
```

`vite.config.ts` proxies `/api` and `/healthz` to `127.0.0.1:8000`, so there is
no CORS configuration in either environment.

## Build

```bash
npm run build     # typecheck + vite build -> dist/
```

`dist/` is **committed on purpose**. The Docker image copies it directly instead
of running a Node build stage, which keeps every Render deploy fast and free of
an npm-registry dependency. **After changing anything in `src/`, run
`npm run build` and commit the new `dist/`** — otherwise the deployed site keeps
serving the old bundle.

## How the streaming works

`src/lib/api.ts` POSTs to `/api/chat` and reads the response body with a
`ReadableStream` reader, splitting SSE frames on blank lines. `EventSource` is
not usable because it only issues GET requests and the chat payload needs a body.

Four event types arrive:

| event | meaning | handled by |
|---|---|---|
| `trace` | one agent step (intent parse, cookbook search) | `AgentTrace` |
| `sources` | the retrieved passages for the latest search | `SourceDrawer` |
| `token` | a chunk of answer text | `AnswerCard` |
| `done` | citations, search count, elapsed ms | `AnswerCard` footer |

`src/hooks/useChat.ts` owns the message list and applies those events to the
in-flight assistant message. Aborting (the Stop button) cancels the fetch via
`AbortController`.

## Layout behaviour

| viewport | rail | source drawer |
|---|---|---|
| > 1080px | fixed column | fixed third column |
| 861–1080px | fixed column | slide-over + scrim |
| ≤ 860px | slide-over sheet | slide-over + scrim |

## Adding a remark/rehype plugin

`AnswerCard` renders the model output through `react-markdown` +
`remark-gfm`. Note that the first line is lifted out as the card title, so
plugins that transform the root node should leave a leading heading or bold
line intact.
