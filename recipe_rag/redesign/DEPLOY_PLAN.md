# 部署方案（FastAPI + Render）

已确认的三个决定：

| 项 | 决定 |
|---|---|
| 语料 | 扩充 —— 加现代菜谱 |
| Embedding | **fastembed**（ONNX，不需要 API key，镜像 ~150MB，512MB 内存可跑） |
| LLM | 环境变量做成可切换，先不定 provider |

---

## 1. 已完成：语料修复（这是真正的 blocker）

**发现**：原语料 `week_2/COLX_563_lab2_Lyken35/lab1_recipes_f.json` 有 137 条，其中**只有 42 条是真的菜谱**。剩下 95 条是小册子的版权页、营销文案、目录——全部被当成菜谱建进了索引（例如索引第 0 条的 `title` 是 `"© 1956 GEN. MILLS INC."`，`instructions` 是 `"You do so many nice special things for the family more often..."`）。

**处理**：
- `scripts/fetch_themealdb.py` 过滤掉 95 条非菜谱，保留 42 条
- 从 TheMealDB（免费、无需 API key）抓取 **789 条**现代菜谱
- 合并去重后 **829 条**

**语料覆盖度变化**：

| 关键词 | 修复前 | 修复后 |
|---|---|---|
| spinach | 0 | 33 |
| pasta | 0 | 73 |
| chicken thigh | 0 | 31 |
| olive oil | 0 | 378 |
| garlic | 1 | 736 |
| tofu | 0 | 21 |

**实测检索效果（同一 embedding 模型，只换语料）**：

| 查询 | 修复前 | 修复后 |
|---|---|---|
| chicken thighs spinach lemon | 0.54 CREAMED CHICKEN / 0.50 SALMON SOUFFLÉ / 0.50 FRITTERS | 0.61 Tandoori chicken / 0.61 Jamaican Curry Chicken / 0.58 Tajine de Poulet |
| 2 servings of pasta, flour | 0.42 BISCUITS / 0.41 PANCAKES / 0.39 BATTER FRANKS | 0.45 Fettucine alfredo / 0.45 Spaghetti alla Carbonara / 0.45 Syrian Spaghetti |
| vegetarian with tofu | 0.34 MEAT TURNOVERS / 0.32 BATTER FRANKS | 0.64 Tofu greens & cashew stir-fry / 0.59 Silken Tofu / 0.52 Ma Po Tofu |

产出（在 `redesign/impl/` 下，需复制到仓库根目录）：

```
impl/scripts/fetch_themealdb.py      抓取 + 清洗
impl/artifacts/recipes_all.json      829 条（1.1 MB，可进 Git）
impl/artifacts/recipes_all.emb       用 MiniLM 建的一次性索引（3.2 MB）
```

> ⚠️ `recipes_all.emb` 是用 MiniLM 建的，切到 fastembed/bge-small 后**必须重建**（一行命令）。

---

## 2. 目标架构

```
recipe-rag/
├── recipe_rag/
│   ├── embedding.py          ★ 新增：可插拔 embedder（fastembed / st / API）
│   ├── vector_store.py       △ 改：pickle → npz + jsonl
│   ├── app.py                △ 改：search_cookbook 透传 result.hits
│   └── config.py             △ 改：provider 可切换
├── services/api/main.py      ★ 新增：FastAPI + SSE
├── scripts/
│   ├── fetch_themealdb.py    ★ 新增
│   └── build_index.py        △ 改：用 embedding.py
├── artifacts/recipes_all.json + recipes_all.npz
├── requirements.txt          △ 改：去 torch，加 fastapi/uvicorn/fastembed
├── Dockerfile                ★ 新增
└── render.yaml               ★ 新增
```

---

## 3. 关键实现点

### 3.1 `search_cookbook` 透传分数

好消息：`retrieval.py` 返回的 `RetrievalResult.hits` **本来就是 `list[(score, entry)]`**，分数一直都在，只是 `app.py` 用 `"\n\n---\n\n".join(result.blocks)` 把它丢了。

```python
@dataclass
class Hit:
    title: str; text: str; score: float; source: str

def search_cookbook(self, query: str) -> list[Hit]:
    r = search_for_prompt(self.embedder, self.vector_store, query, k=4, min_similarity=0.35)
    self.last_hits = [Hit(_title(e), e["text"], s, e["metadata"].get("notes","")) for s, e in r.hits]
    return self.last_hits
```

`min_similarity` 从 **0.15 → 0.35**：实测分数区间是 0.39–0.64，0.15 等于不过滤。

### 3.2 fastembed 替换

```python
# recipe_rag/embedding.py
class FastEmbedEmbedder:
    def __init__(self, model="BAAI/bge-small-en-v1.5"):   # 384 维，比 MiniLM 强
        from fastembed import TextEmbedding
        self._m = TextEmbedding(model)
    def encode(self, text):
        return next(iter(self._m.embed([text])))
```

保持和 `SentenceTransformer.encode` 一样的接口，`retrieval.py` 不用改。

### 3.3 SSE 事件

```
POST /api/chat   {conversationId, message, persona, dietary[], pantry[]}

event: trace    data: {"step":"parse","label":"Parsed intent","ms":200}
event: trace    data: {"step":"search","query":"chicken","hits":4,"ms":900}
event: sources  data: [{"id":1,"title":"Chicken wings with cumin…","score":0.59}, …]
event: token    data: {"t":"Using sharp kitchen scissors, "}
event: done     data: {"messageId":"…","citations":[1,3]}
```

响应头加 `X-Accel-Buffering: no`，否则部分平台会缓冲 SSE。

### 3.4 Dockerfile 要点

```dockerfile
# 模型烤进镜像，避免每次冷启动重下
RUN python -c "from fastembed import TextEmbedding; list(TextEmbedding('BAAI/bge-small-en-v1.5').embed(['warmup']))"
CMD ["uvicorn","services.api.main:app","--host","0.0.0.0","--port","$PORT"]
```

**不要**装 torch —— 那是 2GB 镜像和 512MB 内存爆炸的来源。

### 3.5 render.yaml

```yaml
services:
  - type: web
    name: recipe-rag-api
    runtime: docker
    plan: free          # 0.1 CPU / 512 MB
    healthCheckPath: /healthz
    envVars:
      - key: OPENAI_API
        sync: false      # 在面板里填
      - key: OPENAI_BASE_URL
        value: https://integrate.api.nvidia.com/v1
      - key: OPENAI_MODEL
        value: meta/llama-3.1-70b-instruct
```

> Render `free` = **0.1 CPU / 512 MB**；最便宜的付费档 `0.5c-512mb` **还是 512MB**，要多内存得直接上 `1c-2g`（2GB）。这是选 fastembed 而不是 torch 的原因。

---

## 4. 需要你提供

| 项 | 用途 | 现在有吗 |
|---|---|---|
| GitHub 仓库 | Render 从仓库构建 | ✅ `LykenL/Recipe_RAG` |
| NVIDIA API key | LLM 对话 | ✅ `.env` 里有 |
| Render 账号 | 托管 | ❓ 需要你注册（GitHub 登录即可） |
| 前端托管 | 可选，Vercel/Cloudflare Pages | ❓ 后话 |

**唯一需要你现在做的一件事：注册 Render 并授权 GitHub 仓库。**

---

## 5. 构建顺序

1. `embedding.py` + `vector_store.py`（npz/jsonl）+ 改 `build_index.py` → 重建索引
2. `app.py::search_cookbook` 透传 hits + 阈值改 0.35
3. `services/api/main.py`（FastAPI SSE）
4. `Dockerfile` + `render.yaml` + `requirements.txt`
5. 本地 `docker run` 验证 → push → Render 部署 → 验证公开链接
6. React 前端（另开一轮）

**注意**：`sandbox` 只允许我写 `recipe_rag/` 目录，仓库根目录（`streamlit_app.py`、`services/` 所在层）需要你授权，或者我给你文件 + 一条 `cp` 命令。
