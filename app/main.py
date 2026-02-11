from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base

from app.models.user import User
from app.models.section import Section
from app.models.application import Application
from app.models.section_config import SectionConfig
from app.models.outreach_template import OutreachTemplate
from app.models.outreach_thread import OutreachThread
from app.models.outreach_message import OutreachMessage
from app.models.todo import Todo
from app.models.contact import Contact
from app.models.resume_preset import ResumePreset

from app.routers import auth, sections, applications, generate, ai, outreach, section_configs, jd_matcher, todos, contacts, resume_presets

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Resume Forge API",
    description="API for resume generation and tracking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(sections.router, prefix="/api/sections", tags=["sections"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(outreach.router, prefix="/api/outreach", tags=["outreach"])
app.include_router(section_configs.router, prefix="/api/section-configs", tags=["section-configs"])
app.include_router(jd_matcher.router, prefix="/api/jd", tags=["jd-matcher"])
app.include_router(todos.router, prefix="/api/todos", tags=["todos"])
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(resume_presets.router, prefix="/api/resume-presets", tags=["resume-presets"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}
