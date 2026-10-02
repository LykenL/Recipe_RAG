# 换到 React + Node.js：能好多少，怎么落地

> 效果图：`05-react-empty.png`、`06-react-chat.png`、`07-react-mobile.png`
> 可交互原型：`mockup-react.html`（浏览器直接打开）

---

## 一、这次改了什么

侧边栏原来是 `#191512`（近黑），主区是 `#FAF6F0`（羊皮纸），两者明度差 90%+，放在一起像两块不同的产品拼起来的。

现在改成**暖纸质分层**——rail 比画布略深一点，卡片纯白，形成一个自然的明度阶梯：

| 层 | 色值 | 用途 |
|---|---|---|
| Rail | `#F0E7DA` | 侧栏底 |
| Canvas | `#FAF6F0` | 主区底 |
| Card | `#FFFFFF` | 卡片 / 输入框 |
| 用户气泡 | `#F0E7DA` + 描边 | 对话里唯一的"凹"面 |

深色不再是背景，而是降级为**强调色**（`.btn`、停止按钮、sidebar 序号徽章），品牌感靠 terracotta 渐变 logo 撑住，不再靠一整块黑。

顺带把品牌移到侧栏顶部、顶部换成 58px 轻量上下文栏，侧栏加上了**会话历史列表**——这一条很重要，它是 React 方案最直接的收益，Streamlit 做不了。

---

## 二、React + Node 真的更好吗？分情况

**结论：在前端交互上明显更好，在后端上不一定要 Node。**

| 能力 | Streamlit | React | 差距 |
|---|---|---|---|
| 逐 token 流式 + tool 事件 | ⚠️ 每次 `st.rerun()` 重跑整个脚本，工具调用只能在 chunk 间隙补渲染 | ✅ SSE 原生，`tool_call` / `token` / `sources` 事件各走各的 | **大** |
| 多会话历史 / 分支重生成 | ❌ `session_state` 单会话、随 rerun 抖动 | ✅ 普通状态管理 | **大** |
| ⌘K 命令面板、引用 hover 气泡、停止生成、焦点管理 | ❌ 要写脆弱的 JS hack | ✅ | **大** |
| 设计还原度 | ⚠️ 要和 Streamlit 的 DOM 打 `!important` 官司 | ✅ `mockup-react.html` 的 CSS 直接搬 | 中 |
| 检索质量 / 延迟 / 成本 | — | — | **零** |

最后一行是关键：**换框架不会让你的 RAG 变准**。如果目标是答辩好看、交互顺手，React 值；如果目标是提升回答质量，先改 prompt 和检索。

---

## 三、架构（推荐）

```
recipe-rag/
├── recipe_rag/              ← 不动，Python 后端逻辑全保留
├── services/api/            ← 新增：FastAPI sidecar（~150 行）
│   └── main.py                 POST /api/chat → SSE
│                               GET  /api/conversations
│                               GET  /api/recipes/{id}
└── apps/web/                ← 新增：React 18 + Vite + TS + Tailwind
    ├── src/styles/tokens.css     ← 从 mockup-react.html 抽 :root
    ├── src/features/chat/        ChatThread · Composer · AgentTrace · SourceDrawer
    ├── src/features/kitchen/     PersonaPicker · DietaryToggles · PantryChips
    └── src/lib/sse.ts
```

**Node 要不要？** 只有当你需要鉴权、多用户、限流、Postgres 持久化时，才在 FastAPI 前加一层 Node BFF。否则 Node 只是多一跳，没有任何收益。纯前端 + FastAPI 是最短路径（和现有 Python 零阻抗）。

**为什么不重写 Python？** `retrieval.py` / `relevance.py` / `app.py` 的 ReAct loop 已经能跑，重写风险高且不产生任何用户可见价值。React 只负责渲染它吐出来的事件。

---

## 四、唯一需要动的 Python（1 处）

`app.py::search_cookbook` 现在返回拼好的字符串：

```python
return "\n\n---\n\n".join(result.blocks)          # 分数在 join 时丢了
```

改成返回结构化数据，分数才画得出来（效果图里的 0.57 / 0.52 / 0.51 是真实跑出来的）：

```python
@dataclass
class Hit:
    title: str; text: str; score: float; source: str

def search_cookbook(self, query: str) -> list[Hit]:
    result = search_for_prompt(self.embedder, self.vector_store, query, k=3, ...)
    return [Hit(block.title, block.text, block.score, block.source) for block in result.hits]
```

`llm.agent_loop` 里 `str(tool_result)` 那行相应改成序列化 `list[Hit]`，答案仍然是给 LLM 看的文本，但同一份数据也推给前端。**这一步不做，Sources 抽屉里的相似度就只能是假的。**

---

## 五、接口约定（SSE）

```
POST /api/chat   { conversationId, message, persona, dietary[], pantry[] }

event: trace    data: {"step":"parse","label":"Parsed intent","ms":200}
event: trace    data: {"step":"search","query":"lemon chicken","hits":6,"ms":900}
event: sources  data: [{"id":1,"title":"Oven-Crisp Chicken and Biscuits","score":0.57,...}]
event: token    data: {"t":"Pat the thighs dry, "}
event: done     data: {"messageId":"...","citations":[1,3]}
```

前端 `sse.ts` 逐行解析即可；`AbortController` 直接接效果图里的停止按钮。

---

## 六、分阶段排期

| 阶段 | 工作 | 工期 |
|---|---|---|
| 0 | 把 `:root` tokens 抽成 `tokens.css` + Tailwind config | 0.5d |
| 1 | FastAPI sidecar，`RecipeRAGAssistant.run()` 包成 SSE | 1–2d |
| 2 | React 骨架：Rail + Thread + Composer，先用假数据把效果图 1:1 还原 | 2–3d |
| 3 | 接 SSE：流式 markdown、agent trace 实时更新、停止按钮 | 1–2d |
| 4 | Sources 抽屉接真实分数（依赖第四节的改动） | 1d |
| 5 | 会话持久化（SQLite → Postgres）、历史列表 | 1–2d |

**迁移策略**：Streamlit 版本继续在线，React 版本并行开发，阶段 3 结束时再切。不要一次性推翻——你现在这套后端是能跑的。

---

## 七、风险

- **两套代码 = 两倍维护**。如果这只是一个课程项目，值得认真想想要不要。折中方案：只把「Sources 抽屉 + trace」用 React 嵌入 Streamlit（`st.components.v1.html`），成本 1 天，拿到 60% 的收益。
- **FastAPI + Vite 两个 dev server** 本地开发会烦，用 `concurrently` 或 Vite proxy 解决。
- **流式 markdown 渲染** 会有半截语法闪烁，用 `react-markdown` + 只在 `done` 时做高亮即可。
