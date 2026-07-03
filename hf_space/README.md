---
title: Payment Retry Orchestrator
emoji: 🔁
colorFrom: red
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# Payment Retry Orchestrator

Failed charges retry automatically with exponential backoff. ~30% of synthetic payments fail on the first attempt.

The landing page is an interactive API console — click any endpoint to call the live API.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health + queue depth |
| POST | `/api/charges` | Create a charge (202, saga runs async) |
| GET | `/api/charges/{id}` | Charge status + attempt history |
| GET | `/api/charges` | List recent charges |
| GET | `/api/stats` | Success-rate stats |

## Stack

Python 3.11 · FastAPI · SQLite · Pydantic v2 · Next.js 14 (static export) · Tailwind CSS · Docker
