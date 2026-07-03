# Stage 1: Build Next.js static export
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python API
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend-builder /frontend/out ./frontend/out
RUN mkdir -p /app/data && useradd -m appuser && chown -R appuser:appuser /app/data
USER appuser
ENV DB_PATH=/app/data/app.db
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
