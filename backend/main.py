import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router as api_router
from backend.logger import setup_logger
from backend import models
from backend.db import engine

# Create database tables
models.Base.metadata.create_all(bind=engine)

logger = setup_logger(__name__)

app = FastAPI(title="AI Compiler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API routes
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up AI Compiler FastAPI application.")

@app.get("/")
async def root():
    return {"message": "API is running"}


