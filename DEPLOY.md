# 部署 Recipe RAG Web App（让别人在线访问）

推荐用 **[Streamlit Community Cloud](https://share.streamlit.io)**（免费、和 Streamlit 最省事）。部署后你会得到一个公开链接，例如 `https://your-app.streamlit.app`。

## 部署前检查

确保仓库里包含（已在本项目中准备好）：

| 文件 | 作用 |
|------|------|
| `streamlit_app.py` | 入口（Cloud 默认会找这个文件名） |
| `requirements.txt` | Python 依赖（含 `streamlit`） |
| `recipe_rag/` | RAG 逻辑 |
| `artifacts/recipes.emb` | 向量索引（约 300KB，需提交到 Git） |
| `bg_b64.txt` | 背景图（可选，约 800KB） |

**不要**把 `.env` 或真实 API Key 提交到 GitHub（已在 `.gitignore` 中忽略）。

---

## 步骤 1：推到 GitHub

在项目根目录（`COLX 563` 这一层）：

```bash
cd "/Users/lykenl/Documents/UBC MDSCL/BLOCK 5/COLX 563"
git init
git add streamlit_app.py requirements.txt recipe_rag/ artifacts/ bg_b64.txt .gitignore .streamlit/ DEPLOY.md README_RAG_SHOWCASE.md scripts/
git commit -m "Add deployable Streamlit Recipe RAG app"
```

在 GitHub 新建仓库（Private 或 Public），然后：

```bash
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git branch -M main
git push -u origin main
```

若整个课程文件夹太大，可以只把上述文件单独建一个小仓库，不必包含 `week_*` 里的 notebook。

---

## 步骤 2：Streamlit Cloud 创建应用

1. 打开 [https://share.streamlit.io](https://share.streamlit.io)，用 GitHub 登录。
2. **Create app** → 选你的仓库、`main` 分支。
3. **Main file path** 填：`streamlit_app.py`
4. **App URL** 可自定义子域名（例如 `recipe-rag-chef`）。

---

## 步骤 3：配置 Secrets（API Key）

在 App 页面 → **Settings** → **Secrets**，粘贴（把值换成你自己的）：

```toml
OPENAI_API = "nvapi-xxxxxxxx"
OPENAI_BASE_URL = "https://integrate.api.nvidia.com/v1"
OPENAI_MODEL = "meta/llama-3.1-70b-instruct"
```

保存后点 **Reboot app**。也可参考 `.streamlit/secrets.toml.example`。

本地开发仍用 `.env`；云端只读 Secrets，不会上传 `.env`。

---

## 步骤 4：验证

打开公开链接，问一个简单问题（例如 `cheese snacks ingredients`）。首次提问可能较慢（要下载 embedding 模型），之后会快一些。

---

## 常见问题

**Build 失败 / 找不到模块**  
确认 `requirements.txt` 在仓库根目录，且包含 `streamlit` 和 `sentence-transformers`。

**Missing OPENAI_API**  
在 Streamlit Secrets 里配置 `OPENAI_API`（或 `OPENAI_API_KEY`），然后 Reboot。

**Vector store not found**  
确认 `artifacts/recipes.emb` 已 `git add` 并 push。本地可生成：

```bash
python scripts/build_index.py --recipes week_2/COLX_563_lab2_Lyken35/lab1_recipes_f.json --out artifacts/recipes.emb
```

**NVIDIA 限流（429）**  
免费 API 有 RPM 限制；演示人多时需间隔提问或换付费方案。

**不想公开 API 用量**  
仓库可设为 Private；Streamlit 免费版仍可通过链接分享（需登录 Streamlit 才能管理 Private app 的访问，具体以 Streamlit 当前政策为准）。

---

## 其他托管方式（可选）

- **Hugging Face Spaces**（Streamlit SDK）：类似流程，Secrets 在 Space settings。
- **自建 VPS**：`streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0`，前面加 Nginx + HTTPS；需自己保管 `.env` 和进程。

课程展示一般用 Streamlit Cloud 即可。
