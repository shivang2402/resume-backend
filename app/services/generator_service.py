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


def get_section_content(db: Session, user_id: UUID, section_ref: str) -> Optional[dict]:
    """
    Parse section reference like 'amazon:systems:1.0' and fetch from DB.
    Returns the content dict or None if not found.
    """
    parts = section_ref.split(":")
    if len(parts) == 3:
        key, flavor, version = parts
        section = db.query(Section).filter(
            Section.user_id == user_id,
            Section.key == key,
            Section.flavor == flavor,
            Section.version == version,
        ).first()
    elif len(parts) == 2:
        # Format: key:flavor (use current version)
        key, flavor = parts
        section = db.query(Section).filter(
            Section.user_id == user_id,
            Section.key == key,
            Section.flavor == flavor,
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
        "experiences": ["amazon:systems:1.0", "isro:systems:1.2"],
        "projects": ["kambaz:fullstack:1.0"],
        "skills": "systems_hft:1.0",
        "heading": "default:1.0",  # optional
        "education": "default:1.0",  # optional
    }
    """
    content = {
        "experiences": [],
        "projects": [],
        "skills": None,
        "heading": None,
        "education": None,
    }
    
    # Fetch experiences
    for exp_ref in resume_config.get("experiences", []):
        exp_content = get_section_content(db, user_id, f"experience:{exp_ref}" if ":" not in exp_ref else exp_ref)
        if not exp_content:
            # Try parsing as type:key:flavor:version
            exp_content = get_section_content(db, user_id, exp_ref)
        if exp_content:
            content["experiences"].append(exp_content)
    
    # Fetch projects
    for proj_ref in resume_config.get("projects", []):
        proj_content = get_section_content(db, user_id, f"project:{proj_ref}" if ":" not in proj_ref else proj_ref)
        if not proj_content:
            proj_content = get_section_content(db, user_id, proj_ref)
        if proj_content:
            content["projects"].append(proj_content)
    
    # Fetch skills
    skills_ref = resume_config.get("skills")
    if skills_ref:
        content["skills"] = get_section_content(db, user_id, skills_ref)
    
    # Fetch heading (optional - use default from template if not specified)
    heading_ref = resume_config.get("heading")
    if heading_ref:
        content["heading"] = get_section_content(db, user_id, heading_ref)
    
    # Fetch education (optional - use default from template if not specified)
    education_ref = resume_config.get("education")
    if education_ref:
        content["education"] = get_section_content(db, user_id, education_ref)
    
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
    
    # Generate skills.tex (if custom skills provided)
    if content["skills"]:
        skills_tex = generate_skills_tex(content["skills"])
        with open(os.path.join(src_dir, "skills.tex"), "w") as f:
            f.write(skills_tex)
    
    # Generate heading.tex (if custom heading provided)
    if content["heading"]:
        heading_tex = generate_heading_tex(content["heading"])
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
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", build_dir, resume_tex],
            capture_output=True,
            timeout=timeout,
            cwd=build_dir,
        )
    
    pdf_path = os.path.join(build_dir, "resume.pdf")
    if not os.path.exists(pdf_path):
        # Get error from log
        log_path = os.path.join(build_dir, "resume.log")
        error_msg = "PDF compilation failed"
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                log_content = f.read()
                # Find error lines
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
    # Create temporary build directory
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
        # Cleanup
        shutil.rmtree(build_dir, ignore_errors=True)