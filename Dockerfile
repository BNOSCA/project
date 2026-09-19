FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY data/fixtures ./data/fixtures
ENV BACKEND_MODE=mock APP_DB_PATH=/app/runtime/demo.sqlite3 APP_DATA_DIR=/app/data/fixtures
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
