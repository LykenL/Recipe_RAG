# Recipe RAG API — small ONNX image, no PyTorch.
#
# Size matters here: Render's free instance gives 512MB RAM, and torch alone
# would blow that. fastembed + onnxruntime keeps the image ~150MB and resident
# memory around 120MB.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Bake the model here so it is inside the image, not re-downloaded per boot
    FASTEMBED_CACHE_PATH=/app/.fastembed \
    HF_HOME=/app/.fastembed

WORKDIR /app

# onnxruntime needs libgomp; curl is for the healthcheck
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Download the embedding model at build time. First cold start then pays nothing.
RUN python -c "\
from fastembed import TextEmbedding; \
import numpy as np; \
v = list(TextEmbedding('sentence-transformers/all-MiniLM-L6-v2').embed(['warmup'])); \
print('model baked, dim =', np.asarray(v[0]).shape[0])"

COPY recipe_rag/ ./recipe_rag/
COPY services/ ./services/
COPY artifacts/ ./artifacts/

# NOTE: no `COPY apps/`. That directory does not exist yet, and a COPY of a
# missing path fails the whole build. When you build the React frontend, add:
#     COPY apps/web/dist/ ./apps/web/dist/
# The service already mounts apps/web/dist automatically when it is present.

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT:-8000}/healthz" || exit 1

CMD ["sh", "-c", "uvicorn services.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
