# DawaDrishti: one image that serves the API and the web app.
#   docker build -t dawadrishti . && docker run -p 8000:8000 dawadrishti      -> http://localhost:8000
# The built warehouse, ERP database and model files are in the repo, so nothing is fetched or trained at start-up.

FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY deploy/requirements-runtime.txt ./
RUN pip install -r requirements-runtime.txt
COPY dawadrishti/ dawadrishti/
COPY api/ api/
COPY artifacts/ artifacts/
COPY data/staging/ data/staging/
COPY data/warehouse/ data/warehouse/
COPY data/erp/ data/erp/
COPY data/er/ data/er/
COPY --from=web /web/dist web/dist
RUN useradd --create-home app && chown -R app /app
USER app
EXPOSE 8000
# Render and most hosts pass the port in $PORT
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
