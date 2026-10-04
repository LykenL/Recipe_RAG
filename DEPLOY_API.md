# 部署 Runbook — FastAPI + Render

## 现在仓库里有什么

```
COLX 563/
├── Dockerfile                  ★ 新增  ONNX 镜像，无 torch
├── .dockerignore               ★ 新增  构建上下文 400MB → 5.1MB
├── render.yaml                 ★ 新增  Render Blueprint
├── requirements.txt            △ 重写  API 依赖（去掉 torch / sklearn / streamlit）
├── requirements-streamlit.txt  ★ 新增  原 Streamlit UI 的依赖
├── services/api/main.py        ★ 新增  FastAPI + SSE
├── scripts/fetch_themealdb.py  ★ 新增  抓取 + 清洗语料
├── scripts/build_index.py      △ 重写  输出 npz/jsonl 索引
├── artifacts/recipes_all.json  ★ 新增  829 条菜谱（1.1MB）
├── artifacts/index/            ★ 新增  829×384 ONNX 索引（3.5MB）
└── recipe_rag/
    ├── embedding.py            ★ 新增  可插拔 embedder（fastembed / st / openai）
    ├── vector_store.py         △ 重写  pickle → npz + jsonl
    ├── retrieval.py            △ 重写  sklearn → numpy，向量化
    ├── llm.py                  △ 重写  多轮 history + 无工具降级
    ├── prompting.py            △ 重写  grounded / creative 两种模式
    ├── app.py                  △ 重写  结构化 hits + 阈值可配
    └── __init__.py             △ 重写  惰性导入（否则无 torch 环境下 import 就炸）
```

---

## 本地验证（不需要 Docker）

```bash
cd "/Users/lykenl/Documents/UBC MDSCL/BLOCK 5/COLX 563"

# 1. 建 venv（已建好则跳过）
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt

# 2. 起服务
PYTHONPATH=. ./.venv/bin/uvicorn services.api.main:app --port 8000

# 3. 三个检查
curl -s localhost:8000/healthz
curl -s localhost:8000/api/index
curl -sN -X POST localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"message":"something quick with chicken"}'
```

期望：`/healthz` 返回 `{"status":"ok","recipes":829,...}`；`/api/chat` 依次吐出
`trace → sources → token… → done`。

## 用 Docker 验证（需要先启动 Docker Desktop）

```bash
docker build -t recipe-rag-api .
docker run --rm -p 8000:8000 --env-file .env recipe-rag-api
```

---

## Render 部署

1. 先 `git push`（见下方"提交前检查"）
2. Render Dashboard → **New → Blueprint** → 选 `LykenL/Recipe_RAG`
3. Render 读到 `render.yaml`，建一个 **Web Service（Docker）**
4. 只有 `OPENAI_API` 需要手填（`sync: false`）；其余已在 `render.yaml` 里
5. 部署完访问 `https://recipe-rag-api.onrender.com/healthz`

> 注意：**不要**建 Static Site。`Publish Directory` 是 Static Site 的字段，
> Web Service 没有它。前端以后要么单独建 Static Site（填 `dist`），
> 要么让 FastAPI 直接托管 `apps/web/dist`（一个服务、无 CORS）。

---

## 演示前预热

免费实例闲置约 15 分钟会被回收，下一次请求要付完整启动代价。演示前先打一次：

```bash
curl -s https://recipe-rag-api.onrender.com/warmup | python3 -m json.tool
# {"ready": true, "llm_ok": true, "llm_ms": 1777, "model": "openai/gpt-oss-20b", ...}
```

`ready: true` 就可以开始了。服务启动时也会**自动后台预热一次**（`WARMUP=0` 可关闭），
`/healthz` 的 `llm_warm` 字段反映状态（预热进行中为 `null`）。

**预热能解决什么、不能解决什么：**

| | |
|---|---|
| ✅ 提前校验 key / 模型名，启动日志就能看到错误 | 而不是让第一个提问的人踩到 |
| ✅ 建好到模型服务的 DNS / TLS / 连接 | 第一次提问少付这几百毫秒 |
| ❌ **减少 NVIDIA 免费额度的排队抖动** | 实测同一句查询 16.8s vs 45.9s，纯远端排队 |

想进一步减少冷启动，可以把这个 URL 丢给免费 uptime 监控（UptimeRobot 之类）定时打。

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `OPENAI_API` | — | **必填**，NVIDIA key |
| `OPENAI_BASE_URL` | `https://integrate.api.nvidia.com/v1` | 换 provider 只改这里 |
| `OPENAI_MODEL` | `nvidia/nemotron-3-super-120b-a12b` | 见下方"模型实测" |
| `EMBEDDING_BACKEND` | `fastembed` | `fastembed` / `st` / `openai` |
| `ANSWER_MODE` | `grounded` | `grounded` 只从检索结果回答；`creative` 允许即兴发挥 |
| `MAX_ITERATIONS` | `3` | 每多一轮就多一次模型调用，直接决定延迟 |
| `ALLOWED_ORIGINS` | `*` | 有了前端后收紧 |
| `INDEX_PATH` | `artifacts/index` | 换索引位置 |
| `WARMUP` | `1` | 设为 `0` 关闭启动时的后台预热 |
| `MAX_SEARCHES` | `2` | 单次回答最多检索几轮，**由代码强制**而非写在 prompt 里 |
| `FORCE_FIRST_SEARCH` | `0` | 设为 `1` 强制第一轮必须检索。**默认关闭**，原因见下 |

### 为什么不强制第一次检索（实测）

我试过开启它。它确实消除了"模型不查菜谱直接凭记忆回答"，但**弄坏了一个本来正常的场景**：

| 问题（已声明坚果过敏） | 强制前 | 强制后 |
|---|---|---|
| "a dessert with nuts" | 6.3s，清晰拒绝：*"我不能提供含坚果的甜点，因为你有坚果过敏"* | 检索 4 次后**什么都不输出**（推理耗尽预算） |

而且原来的行为**并不是不诚实**：没有检索的回答，界面本来就写着 `No cookbook match — answered without sources`，trace 里也写着 `No cookbook search was needed for this question`。

所以默认关闭，保留 `FORCE_FIRST_SEARCH=1` 作为可选项。

### 模型实测（OPENAI_BASE_URL = NVIDIA）

`meta/llama-3.1-70b-instruct` **已于 2026-08-26 下线**，原配置直接 410。

| 模型 | 工具调用 | 延迟 | 结论 |
|---|---|---|---|
| `nvidia/nemotron-3-super-120b-a12b` | ✅ | ~14–25s | **默认，唯一同时正确+可用** |
| `z-ai/glm-5.3-flash` | ✅ | ~64s | 太慢 |
| `openai/gpt-oss-20b` | ✅ | ~10s | 快，但会一直调工具不收敛 |
| `z-ai/glm-5.3` / `google/gemma-4-31b-it` | ✅ | 未测延迟 | 备选 |
| nemotron-70b/51b、mistral-large、yi-large、jamba | ❌ | — | `Function ... Not found for account` |

---

## 重建索引（换 embedding 模型或换语料时）

```bash
# 1. 重建语料（TheMealDB，免费无需 key）
python scripts/fetch_themealdb.py --out artifacts/recipes_all.json

# 2. 重建索引
python scripts/build_index.py --recipes artifacts/recipes_all.json --out artifacts/index
```

⚠️ **换 embedding 模型必须重建索引**，`app.py` 会在加载时校验维度和模型名并报错。

---

## 关键设计决定（都有实测依据）

- **不用 torch**：Render free 是 0.1 CPU / **512MB**，torch 运行时吃 400–600MB。
  换 ONNX 后镜像 ~150MB、内存 ~120MB。验证过：在没有 torch 和
  sentence-transformers 的环境里，`import recipe_rag.*` 与编码都正常。
- **embedding 用 MiniLM 而不是 bge-small**：bge 在 MTEB 上更强，但实测
  相关查询 0.605 / 不相关 0.600，**分离度 +0.005**，阈值完全失效；
  MiniLM 是 0.460 / 0.288，**分离度 +0.172**。小语料上分离度比榜单排名重要。
- **阈值 0.35**：实测相关查询 0.46–0.66，不相关 <0.29。0.15（原值）等于不过滤。
- **`ANSWER_MODE=grounded`**：原来的 prompt 明确要求"绝不承认找不到、
  直接编一个、不要提检索到的内容"，而 UI 却写"每句话都可溯源"。两者不能并存。
  改成 grounded 后，同一个问题从"编造的 Garlic-Lemon Chicken Skillet"
  变成"Based on **Sticky Chicken**"+ 原文配料。
- **语料清洗**：原 137 条里只有 42 条是真菜谱，95 条是小册子版权页/营销文案。
  清洗 + 扩充到 829 条后，`tofu` 查询从返回 `MEAT TURNOVERS` 变成 `Tofu stir-fry`。

---

## 提交前检查

```bash
git status --short
```

必须确认 **没有** 提交 `.env`、`.venv-index/`、`recipe_rag/redesign/impl/.venv-index/`。
`.gitignore` 已加 `.venv*/`，但提交前还是看一眼。

```bash
git add Dockerfile .dockerignore render.yaml \
        requirements.txt requirements-streamlit.txt \
        services/ scripts/ artifacts/ recipe_rag/
git commit -m "Add FastAPI + SSE backend, ONNX embeddings, cleaned 829-recipe corpus"
git push
```

---

## 已知限制

- Render free 闲置 15 分钟休眠，冷启动约 30–60s（模型已烤进镜像，不用重下）
- 语料是 TheMealDB 英文菜谱，没有中文
- `serving_size` 在 TheMealDB 里不存在，索引里记作 `[0, 0]`（未知）
- 会话历史目前由前端持有并回传，服务端无状态；多会话持久化还没做
