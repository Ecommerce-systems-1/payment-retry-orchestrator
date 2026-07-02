FROM node:20-slim AS fb
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
COPY --from=fb /frontend/out ./frontend/out
RUN useradd -m appuser
USER appuser
EXPOSE 7860
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "7860"]
