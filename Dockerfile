# Beemer — portable container image (Render, Railway, Google Cloud Run, Fly.io, Hugging Face Spaces, any VPS).
#   docker build -t beemer .
#   docker run --rm -p 8501:8501 beemer            → http://localhost:8501
# The image ships without data; on start it downloads the latest published snapshot (bootstrap.py).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8501

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# uid 1000 = what Hugging Face Spaces expects; data/ and logs/ must be writable for the bootstrap
RUN useradd --create-home --uid 1000 beemer \
 && mkdir -p data logs \
 && chown -R beemer:beemer /app
USER beemer

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/_stcore/health" || exit 1

# PORT is injected by most hosts (Render, Railway, Cloud Run); 8501 otherwise
CMD ["sh", "-c", "python bootstrap.py || echo 'data bootstrap failed - the app will retry'; exec streamlit run app/main.py --server.port=${PORT} --server.address=0.0.0.0"]
