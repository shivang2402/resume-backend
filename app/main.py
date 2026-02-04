from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base

# Import models so they register with Base before create_all
from app.models.user import User
from app.models.section import Section
from app.models.application import Application

from app.routers import auth, sections, applications, generate, ai

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Resume Forge API",
    description="API for resume generation and tracking",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(sections.router, prefix="/api/sections", tags=["sections"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}
