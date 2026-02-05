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

from app.routers import auth, sections, applications, generate, ai, outreach, section_configs, jd_matcher, sections_v2, jd_matcher_v2

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
app.include_router(sections_v2.router, prefix="/api/v2/sections", tags=["sections-v2"])
app.include_router(jd_matcher_v2.router, prefix="/api/v2/jd", tags=["jd-matcher-v2"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}
