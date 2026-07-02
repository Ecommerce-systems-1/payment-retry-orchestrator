FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./src/
COPY --from=frontend-builder /frontend/out ./frontend/out
RUN mkdir -p /app/data && useradd -m appuser && chown -R appuser:appuser /app/data
USER appuser
ENV DB_PATH=/app/data/data.db
EXPOSE 7860
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
