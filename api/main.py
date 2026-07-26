from fastapi import FastAPI

from api.routers import health, jobs

app = FastAPI(title="ocr-engine", version="0.1.0")

app.include_router(jobs.router)
app.include_router(health.router)
