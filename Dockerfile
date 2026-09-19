FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt
COPY backend ./backend
COPY data/catalog/combined/products.json data/catalog/combined/posts.json data/catalog/combined/creators.json ./data/catalog/combined/
COPY data/catalog/kaggle_500/images ./data/catalog/kaggle_500/images
RUN ln -s ../kaggle_500/images ./data/catalog/combined/images
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
ENV BACKEND_MODE=mock APP_DB_PATH=/app/runtime/demo.sqlite3 APP_DATA_DIR=/app/data/catalog/combined
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
