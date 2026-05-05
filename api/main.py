import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.pipeline import router as pipeline_router

app = FastAPI(
    title       = "SECFAOS API",
    description = "Smart Energy Consumption Forecasting and Optimisation System",
    version     = "1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://localhost:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(pipeline_router, prefix="/api/pipeline", tags=["Pipeline"])

@app.get("/")
async def root():
    return {"message": "SECFAOS API running", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "ok"}