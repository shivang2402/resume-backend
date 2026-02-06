"""
JD Matcher - Unified router with tag-based matching.
Uses pre-computed tags for fast matching (2 AI calls).
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import uuid

from app.database import get_db
from app.models.section import Section
from app.models.section_config import SectionConfig
from app.services.jd_extractor import extract_jd_terms
from app.services.jd_matcher_service import match_sections_to_jd
from app.services.keyword_service import find_missing_keywords_with_ai, sections_to_text
from app.schemas.jd_matcher import (
    JDAnalyzeRequest,
    JDAnalyzeResponse,
    KeywordRecalcRequest,
    KeywordRecalcResponse,
    Suggestions,
    SectionSuggestion,
    AllSections,
    AllSectionInfo,
    FlavorInfo,
    SkillsInfo
)

router = APIRouter()


def get_user_id(x_user_id: str = Header(..., alias="X-User-ID")) -> uuid.UUID:
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")


def get_sections_with_tags(db: Session, user_id: uuid.UUID) -> Dict[str, List]:
    """Fetch sections with their pre-computed tags."""
    sections = db.query(Section).filter(
        Section.user_id == user_id,
        Section.is_current == True
    ).all()
    
    grouped = {'experiences': [], 'projects': [], 'skills': []}
    by_type_key = {}
    
    for s in sections:
        type_key = (s.type, s.key)
        if type_key not in by_type_key:
            by_type_key[type_key] = []
        by_type_key[type_key].append(s)
    
    for (section_type, key), section_list in by_type_key.items():
        if section_type == 'experience':
            flavors = [{'flavor': s.flavor, 'version': s.version, 'tags': s.content.get('tags', []), 'content': s.content} for s in section_list]
            grouped['experiences'].append({'key': key, 'flavors': flavors})
        elif section_type == 'project':
            flavors = [{'flavor': s.flavor, 'version': s.version, 'tags': s.content.get('tags', []), 'content': s.content} for s in section_list]
            grouped['projects'].append({'key': key, 'flavors': flavors})
        elif section_type == 'skills':
            for s in section_list:
                grouped['skills'].append({'flavor': s.flavor, 'version': s.version, 'tags': s.content.get('tags', []), 'content': s.content})
    
    return grouped


def get_section_configs_map(db: Session, user_id: uuid.UUID) -> Dict[str, Dict]:
    configs = db.query(SectionConfig).filter(SectionConfig.user_id == user_id).all()
    return {f"{c.section_type}:{c.section_key}": {'priority': c.priority, 'fixed_flavor': c.fixed_flavor} for c in configs}


def filter_by_priority(sections: Dict[str, List], configs: Dict[str, Dict]) -> Dict[str, List]:
    filtered = {'experiences': [], 'projects': [], 'skills': sections['skills']}
    for exp in sections['experiences']:
        config = configs.get(f"experience:{exp['key']}", {'priority': 'normal'})
        if config['priority'] != 'never':
            filtered['experiences'].append(exp)
    for proj in sections['projects']:
        config = configs.get(f"project:{proj['key']}", {'priority': 'normal'})
        if config['priority'] != 'never':
            filtered['projects'].append(proj)
    return filtered


def get_pinned_sections(sections: Dict[str, List], configs: Dict[str, Dict]) -> List[Dict]:
    pinned = []
    for exp in sections['experiences']:
        config = configs.get(f"experience:{exp['key']}", {'priority': 'normal'})
        if config['priority'] == 'always':
            pinned.append({'type': 'experience', 'key': exp['key'], 'flavor': config.get('fixed_flavor')})
    for proj in sections['projects']:
        config = configs.get(f"project:{proj['key']}", {'priority': 'normal'})
        if config['priority'] == 'always':
            pinned.append({'type': 'project', 'key': proj['key'], 'flavor': config.get('fixed_flavor')})
    return pinned


def build_all_sections_response(sections: Dict[str, List], configs: Dict[str, Dict]) -> AllSections:
    experiences = [AllSectionInfo(
        key=exp['key'],
        flavors=[FlavorInfo(flavor=f['flavor'], version=f['version']) for f in exp['flavors']],
        priority=configs.get(f"experience:{exp['key']}", {'priority': 'normal'})['priority'],
        fixed_flavor=configs.get(f"experience:{exp['key']}", {}).get('fixed_flavor')
    ) for exp in sections['experiences']]
    
    projects = [AllSectionInfo(
        key=proj['key'],
        flavors=[FlavorInfo(flavor=f['flavor'], version=f['version']) for f in proj['flavors']],
        priority=configs.get(f"project:{proj['key']}", {'priority': 'normal'})['priority'],
        fixed_flavor=configs.get(f"project:{proj['key']}", {}).get('fixed_flavor')
    ) for proj in sections['projects']]
    
    skills = [SkillsInfo(flavor=s['flavor'], version=s['version']) for s in sections['skills']]
    
    return AllSections(experiences=experiences, projects=projects, skills=skills)


def get_version_for_section(sections: Dict[str, List], section_type: str, key: str, flavor: str) -> str:
    type_key = 'experiences' if section_type == 'experience' else 'projects'
    for item in sections.get(type_key, []):
        if item['key'] == key:
            for f in item['flavors']:
                if f['flavor'] == flavor:
                    return f['version']
    return '1.0'


@router.post("/analyze")
async def analyze_jd(
    request: JDAnalyzeRequest,
    x_gemini_api_key: str = Header(..., alias="X-Gemini-API-Key"),
    user_id: uuid.UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Analyze JD using pre-computed tags. 2 AI calls, ~500-700 tokens."""
    
    if not x_gemini_api_key or len(x_gemini_api_key) < 20:
        raise HTTPException(status_code=400, detail="Invalid Gemini API key")
    
    sections = get_sections_with_tags(db, user_id)
    
    if not sections['experiences'] and not sections['projects'] and not sections['skills']:
        raise HTTPException(status_code=400, detail="No content found. Add sections first.")
    
    configs = get_section_configs_map(db, user_id)
    filtered_sections = filter_by_priority(sections, configs)
    pinned_sections = get_pinned_sections(sections, configs)
    
    # AI Call 1: Extract JD terms
    jd_extracted = await extract_jd_terms(x_gemini_api_key, request.job_description)
    jd_terms = jd_extracted.get('terms', [])
    
    if request.additional_instructions:
        jd_terms.append(f"Note: {request.additional_instructions}")
    
    # AI Call 2: Match sections
    try:
        match_result = await match_sections_to_jd(
            api_key=x_gemini_api_key,
            jd_terms=jd_terms,
            jd_info=jd_extracted,
            sections_with_tags=filtered_sections,
            pinned_sections=pinned_sections
        )
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Resource exhausted" in error_msg:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment and try again.")
        raise HTTPException(status_code=500, detail=f"AI matching failed: {error_msg}")
    
    # Build response
    exp_suggestions = [SectionSuggestion(
        key=e['key'],
        flavor=e['flavor'],
        version=get_version_for_section(sections, 'experience', e['key'], e['flavor']),
        pinned=any(p['key'] == e['key'] for p in pinned_sections),
        reason=e.get('reason', '')
    ) for e in match_result.get('experiences', [])]
    
    proj_suggestions = [SectionSuggestion(
        key=p['key'],
        flavor=p['flavor'],
        version=get_version_for_section(sections, 'project', p['key'], p['flavor']),
        pinned=any(pin['key'] == p['key'] for pin in pinned_sections),
        reason=p.get('reason', '')
    ) for p in match_result.get('projects', [])]
    
    return {
        "suggestions": {
            "skills_flavor": match_result.get('skills_flavor', 'default'),
            "experiences": exp_suggestions,
            "projects": proj_suggestions
        },
        "missing_keywords": match_result.get('missing_keywords', []),
        "all_sections": build_all_sections_response(sections, configs),
        "jd_info": jd_extracted
    }


@router.post("/recalculate-keywords", response_model=KeywordRecalcResponse)
async def recalculate_keywords(
    request: KeywordRecalcRequest,
    x_gemini_api_key: str = Header(None, alias="X-Gemini-API-Key"),
    user_id: uuid.UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Recalculate missing keywords based on current selection. No full Gemini call."""
    
    # Get selected sections content
    selected_content = []
    for selection in request.selected_sections:
        section = db.query(Section).filter(
            Section.user_id == user_id,
            Section.type == selection.type,
            Section.key == selection.key,
            Section.flavor == selection.flavor,
            Section.is_current == True
        ).first()
        if section:
            selected_content.append(section.content)
    
    # Apply temp edits if any
    if request.temp_edits:
        for section_id, edit in request.temp_edits.items():
            if hasattr(edit, 'content'):
                selected_content.append(edit.content if isinstance(edit.content, dict) else edit.content.model_dump())
    
    # Convert to text
    resume_text = sections_to_text(selected_content)
    
    # Find missing keywords (uses simpler matching or AI if key provided)
    if x_gemini_api_key:
        missing = await find_missing_keywords_with_ai(
            api_key=x_gemini_api_key,
            job_description=request.job_description,
            resume_content=resume_text
        )
    else:
        # Fallback: simple keyword extraction without AI
        from app.services.keyword_service import find_missing_keywords_simple
        missing = find_missing_keywords_simple(request.job_description, resume_text)
    
    return KeywordRecalcResponse(missing_keywords=missing)