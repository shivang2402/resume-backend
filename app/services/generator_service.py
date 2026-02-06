import os
import shutil
import subprocess
import tempfile
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session

from app.models.section import Section
from app.utils.latex import (
    generate_experience_tex,
    generate_projects_tex,
    generate_skills_tex,
    generate_heading_tex,
)


TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")


def get_section_content(db: Session, user_id: UUID, section_type: str, section_ref: str) -> Optional[dict]:
    """
    Parse section reference like 'amazon:systems:1.0' or 'amazon:systems' and fetch from DB.
    section_type: 'experience', 'project', 'skills', 'heading', 'education', 'location', 'email'
    section_ref: 'key:flavor:version' or 'key:flavor' or 'key'
    Returns the content dict or None if not found.
    """
    parts = section_ref.split(":")
    
    if len(parts) == 3:
        key, flavor, version = parts
        section = db.query(Section).filter(
            Section.user_id == user_id,
            Section.type == section_type,
            Section.key == key,
            Section.flavor == flavor,
            Section.version == version,
        ).first()
    elif len(parts) == 2:
        # Format: key:flavor (use current version)
        key, flavor = parts
        section = db.query(Section).filter(
            Section.user_id == user_id,
            Section.type == section_type,
            Section.key == key,
            Section.flavor == flavor,
            Section.is_current == True,
        ).first()
    elif len(parts) == 1:
        # Format: just key (use default flavor, current version)
        key = parts[0]
        section = db.query(Section).filter(
            Section.user_id == user_id,
            Section.type == section_type,
            Section.key == key,
            Section.is_current == True,
        ).first()
    else:
        return None
    
    if section:
        return section.content
    return None


def build_resume_content(db: Session, user_id: UUID, resume_config: dict) -> dict:
    """
    Fetch all sections based on resume_config and return structured content.
    
    resume_config format:
    {
        "location": "boston:default:1.0" or "boston",
        "email": "personal:default:1.0" or "personal",
        "experiences": ["amazon:systems:1.0", "isro:systems:1.2"],
        "projects": ["kambaz:fullstack:1.0"],
        "skills": "systems_hft:1.0" or "systems:1.0",
        "heading": "default:1.0",  # optional
        "education": "default:1.0",  # optional
    }
    """
    content = {
        "location": None,
        "email": None,
        "experiences": [],
        "projects": [],
        "skills": None,
        "heading": None,
        "education": None,
    }
    
    # Fetch location
    location_ref = resume_config.get("location")
    if location_ref:
        content["location"] = get_section_content(db, user_id, "location", location_ref)
    
    # Fetch email
    email_ref = resume_config.get("email")
    if email_ref:
        content["email"] = get_section_content(db, user_id, "email", email_ref)
    
    # Fetch experiences
    for exp_ref in resume_config.get("experiences", []):
        exp_content = get_section_content(db, user_id, "experience", exp_ref)
        if exp_content:
            content["experiences"].append(exp_content)
    
    # Fetch projects
    for proj_ref in resume_config.get("projects", []):
        proj_content = get_section_content(db, user_id, "project", proj_ref)
        if proj_content:
            content["projects"].append(proj_content)
    
    # Fetch skills
    skills_ref = resume_config.get("skills")
    if skills_ref:
        content["skills"] = get_section_content(db, user_id, "skills", skills_ref)
    
    # Fetch heading (optional)
    heading_ref = resume_config.get("heading")
    if heading_ref:
        content["heading"] = get_section_content(db, user_id, "heading", heading_ref)
    
    # Fetch education (optional)
    education_ref = resume_config.get("education")
    if education_ref:
        content["education"] = get_section_content(db, user_id, "education", education_ref)
    
    return content


def generate_latex_files(content: dict, build_dir: str) -> None:
    """
    Generate dynamic .tex files in the build directory.
    """
    src_dir = os.path.join(build_dir, "src")
    os.makedirs(src_dir, exist_ok=True)
    
    # Generate experience.tex
    if content["experiences"]:
        exp_tex = generate_experience_tex(content["experiences"])
        with open(os.path.join(src_dir, "experience.tex"), "w") as f:
            f.write(exp_tex)
    
    # Generate projects.tex
    if content["projects"]:
        proj_tex = generate_projects_tex(content["projects"])
        with open(os.path.join(src_dir, "projects.tex"), "w") as f:
            f.write(proj_tex)
    
    # Generate skills.tex
    if content["skills"]:
        skills_tex = generate_skills_tex(content["skills"])
        with open(os.path.join(src_dir, "skills.tex"), "w") as f:
            f.write(skills_tex)
    
    # Generate heading.tex (with location/email overrides)
    location_value = None
    email_value = None
    
    if content["location"]:
        location_value = content["location"].get("value")
    
    if content["email"]:
        email_value = content["email"].get("value")
    
    # Only generate heading if we have overrides or heading content
    if location_value or email_value or content["heading"]:
        heading_tex = generate_heading_tex(
            heading=content["heading"],
            location=location_value,
            email=email_value
        )
        with open(os.path.join(src_dir, "heading.tex"), "w") as f:
            f.write(heading_tex)


def compile_pdf(build_dir: str, timeout: int = 60) -> bytes:
    """
    Run pdflatex and return PDF bytes.
    """
    resume_tex = os.path.join(build_dir, "resume.tex")
    
    # Run pdflatex twice (for references)
    for _ in range(2):
        result = subprocess.run(
            ["/Library/TeX/texbin/pdflatex", "-interaction=nonstopmode", "-output-directory", build_dir, resume_tex],
            capture_output=True,
            timeout=timeout,
            cwd=build_dir,
        )
    
    pdf_path = os.path.join(build_dir, "resume.pdf")
    if not os.path.exists(pdf_path):
        log_path = os.path.join(build_dir, "resume.log")
        error_msg = "PDF compilation failed"
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                log_content = f.read()
                errors = [line for line in log_content.split("\n") if line.startswith("!")]
                if errors:
                    error_msg = "\n".join(errors[:5])
        raise Exception(error_msg)
    
    with open(pdf_path, "rb") as f:
        return f.read()


def generate_resume(db: Session, user_id: UUID, resume_config: dict) -> bytes:
    """
    Main function: fetch content, generate LaTeX, compile PDF, return bytes.
    """
    build_dir = tempfile.mkdtemp(prefix="resume_build_")
    
    try:
        # Copy template files to build directory
        shutil.copy(os.path.join(TEMPLATES_DIR, "resume.tex"), build_dir)
        shutil.copy(os.path.join(TEMPLATES_DIR, "custom-commands.tex"), build_dir)
        
        # Copy src directory (default templates)
        src_dest = os.path.join(build_dir, "src")
        shutil.copytree(os.path.join(TEMPLATES_DIR, "src"), src_dest)
        
        # Fetch content from database
        content = build_resume_content(db, user_id, resume_config)
        
        # Generate dynamic .tex files (overwrites defaults)
        generate_latex_files(content, build_dir)
        
        # Compile PDF
        pdf_bytes = compile_pdf(build_dir)
        
        return pdf_bytes
    
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)