# Recipe RAG 前端重构方案（Mise）

> 目标：把「一次性问答表单」改造成「会展示检索证据的对话式 Agent 产品」。
> 产物：`mockup.html`（可交互原型）、`01–04*.png`（效果图）、`streamlit_app_v2.py`（可直接替换的实现）。

---

## 一、现状诊断：截图里的 8 个硬伤

| # | 问题 | 证据 | 影响 |
|---|---|---|---|
| 1 | **双输入框打架** | 「YOUR QUESTION」上方还有一个约 300px 高的空玻璃框，无标签、无内容 | 用户不知道哪个才是要填的；第一屏有效信息被吃掉一半 |
| 2 | **对比度严重不足** | 侧栏 `Friendly Home Cook` 深字压深底；副标题/placeholder 约 `#8a8a8a` on `#0a0c10`（≈2.6:1）；正文行距字重都很飘 | WCAG AA 不达标，投影/教室演示基本看不见 |
| 3 | **What's in your fridge 是空白框** | `st.multiselect` 被全局 CSS 覆盖成白底白字 | 控件直接失效，用户以为坏了 |
| 4 | **复选框没有可点击感** | 三个裸白色小方块，无边框/无勾选态/无 hover | 不知道是勾选框还是装饰 |
| 5 | **不是对话产品** | 无历史消息、无 follow-up、回答完就结束 | 与「agentic」定位矛盾；追问成本极高 |
| 6 | **Agent 是黑盒** | 调用 `search_cookbook`、命中几条、阈值多少，全部不可见 | 这是 RAG 项目最该展示的部分，却完全浪费 |
| 7 | **无出处** | `app.py` 已返回 `result.blocks` 和相似度，UI 全部丢弃 | 幻觉无法核验，答辩时没有说服力 |
| 8 | **首屏浪费 + 背景干扰** | Hero 占掉约 45% 首屏；酒杯/蒜头背景压在正文与输入框上；`background-attachment:fixed` + 800KB base64 PNG | 答案永远在折叠线以下；首屏加载变慢 |

---

## 二、重构方向

**一句话**：从「表单」变成「厨房里的对话」，并把 Agent 的检索过程变成产品的一部分。

1. **Chat-first** — 历史消息常驻，底部固定输入框，支持连续追问。
2. **证据优先** — 每条回答都带打分过的来源卡片；被过滤掉的候选也显示（说明为什么排除）。
3. **Agent 可见** — 内联 trace：解析意图 → 向量检索 → 阈值过滤 → 生成，每步带耗时。
4. **高对比暖色系** — 放弃「黑底 + 灰字」，改用羊皮纸底 + 深墨字（正文 ≈9.4:1），深色只留给侧栏做品牌锚点。
5. **单一输入面** — 一个 composer，pantry/饮食限制以 chip 形式挂在输入框上方，随时可撤销。

---

## 三、设计系统

```
画布  #FAF6F0   卡片 #FFFFFF   次级面 #F5EFE6
侧栏  #191512   侧栏描边 #332C25
正文  #17130E / #3D362E        次要 #6E6459 / #9A9086
强调  #CE4A18 (terracotta)     辅助 #E9A03B (saffron)
语义  #3E7A4F (安全/命中)  #FDF0E8 (提示底)
分隔  #EBE2D6
```

- **字体**：标题 `Fraunces`（衬线，食物类产品有温度）；正文/控件 `Inter`。
- **圆角**：卡片 13–20px，chip 999px，输入框 16px。
- **阴影**：只三级，`0 8px 24px -8px rgba(31,23,15,.18)` 为主，避免旧版到处发光。
- **图标**：统一线性 SVG，不再混用 emoji 当图标（旧版标题里 👨‍🍳/🥦/🧊/⚡ 字号风格全不一致）。

---

## 四、三张效果图

| 图 | 场景 | 重点 |
|---|---|---|
| `01-empty-state.png` | 首屏 / 空状态 | Hero 压缩到 1 屏内可见 composer；Quick starts 变成 4 张信息密度更高的入口卡 |
| `02-conversation.png` | 对话 + 回答 | 左侧 trace、中间答案卡（配料勾选 + 步骤 + Chef's note）、右侧 Sources 抽屉（含被拒绝的候选） |
| `03-mobile.png` | 移动端 430×932 | 侧栏折叠成 Pantry 条；来源变成横向滑动卡 |
| `04-before-after.png` | 对比图 | 直接用于答辩/汇报 |

---

## 五、落地到 Streamlit

`streamlit_app_v2.py` 已经按上面实现，直接放到仓库根目录：

```bash
cp recipe_rag/redesign/streamlit_app_v2.py ./streamlit_app_v2.py
streamlit run streamlit_app_v2.py
```

关键实现点：

1. **可观测的 Agent**：`TracedAssistant` 包一层 `search_cookbook`，把 tool 调用的 query 和返回块数记下来，UI 就能画 trace。`app.py` 无需改动。
2. **答案卡样式**：用 `st.container(key="answer_card")`，Streamlit ≥1.39 会生成 `.st-key-answer_card`，CSS 直接命中，不需要把 markdown 包进裸 `<div>`（旧版那种 `st.markdown('<div>')` 其实不会真正嵌套）。
3. **流式渲染**：`trace_slot` / `answer_slot` 两个 `st.empty()`，边 yield 边更新；trace 在检索发生的瞬间就会出现。
4. **Quick starts**：写 `st.session_state.pending`，下一轮当作用户输入处理（`st.chat_input` 不能被预填）。
5. **删掉的东西**：`bg_b64.txt` 的 800KB 背景、`background-attachment:fixed`、`#MainMenu,footer,header{visibility:hidden}` 之外的所有 `!important` 打仗。

### 仍建议补的两件事

- **右键「Browse 137 recipes」还没做**：目前 `retrieval.py` 已返回相似度，加一个浏览页（按分类/相似度）成本很低，能显著提升「这也像个产品」的感觉。
- **相似度是前端算的**：`_sources_html()` 里的分数目前是按序号递减的占位值。要显示真实分数，需让 `search_cookbook` 返回结构化 `(block, score)` 而不是拼好的字符串 —— 建议改 `app.py::search_cookbook`，把 score 一并塞进 trace。

---

## 六、验收清单

- [ ] 所有正文文字对比度 ≥ 4.5:1
- [ ] 首屏（1440×900）内 composer 完全可见，无需滚动
- [ ] 每个回答下方都有来源卡片，且能点开对应菜谱
- [ ] trace 在检索完成后 200ms 内出现，不是等回答结束才一起刷出来
- [ ] 移动端 430px 下无横向滚动
