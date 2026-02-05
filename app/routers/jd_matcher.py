from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uuid

from app.database import get_db
from app.models.section import Section
from app.models.section_config import SectionConfig
from app.services.gemini_service import (
    analyze_jd_with_gemini,
    GeminiError,
    GeminiAuthError,
    GeminiRateLimitError
)
from app.services.keyword_service import (
    find_missing_keywords_with_ai,
    sections_to_text,
    content_to_text,
    KeywordServiceError
)
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

def get_user_id(x_user_id: str = Header(...)) -> uuid.UUID:
    """Extract user ID from header."""
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

def get_user_sections(db: Session, user_id: uuid.UUID) -> Dict[str, List]:
    """Fetch all current sections grouped by type."""
    sections = db.query(Section).filter(
        Section.user_id == user_id,
        Section.is_current == True
    ).all()
    
    grouped = {
        'experiences': [],
        'projects': [],
        'skills': []
    }
    
    # Group by type and key
    by_type_key = {}
    for s in sections:
        type_key = (s.type, s.key)
        if type_key not in by_type_key:
            by_type_key[type_key] = []
        by_type_key[type_key].append(s)
    
    for (section_type, key), section_list in by_type_key.items():
        if section_type == 'experience':
            flavors = []
            for s in section_list:
                content_summary = summarize_content(s.content)
                flavors.append({
                    'flavor': s.flavor,
                    'version': s.version,
                    'content_summary': content_summary,
                    'content': s.content
                })
            grouped['experiences'].append({
                'key': key,
                'flavors': flavors
            })
        elif section_type == 'project':
            flavors = []
            for s in section_list:
                content_summary = summarize_content(s.content)
                flavors.append({
                    'flavor': s.flavor,
                    'version': s.version,
                    'content_summary': content_summary,
                    'content': s.content
                })
            grouped['projects'].append({
                'key': key,
                'flavors': flavors
            })
        elif section_type == 'skills':
            for s in section_list:
                content_summary = summarize_content(s.content)
                grouped['skills'].append({
                    'flavor': s.flavor,
                    'version': s.version,
                    'content_summary': content_summary,
                    'content': s.content
                })
    
    return grouped

def summarize_content(content: Dict) -> str:
    """Create a BRIEF summary of section content for the prompt (token-efficient)."""
    parts = []
    if 'title' in content or 'role' in content:
        parts.append(content.get('title') or content.get('role', ''))
    if 'company' in content:
        parts.append(content['company'])
    if 'bullets' in content and content['bullets']:
        # Only first bullet, max 50 chars
        first = content['bullets'][0][:50]
        parts.append(first + "..." if len(content['bullets'][0]) > 50 else first)
    if 'skills' in content:
        if isinstance(content['skills'], dict):
            # Just category names
            parts.append(f"Categories: {', '.join(list(content['skills'].keys())[:3])}")
        elif isinstance(content['skills'], list):
            parts.append(', '.join(content['skills'][:5]))
    if 'name' in content:
        parts.append(content['name'])
    if 'tech' in content or 'tech_stack' in content:
        tech = content.get('tech') or content.get('tech_stack', [])
        if isinstance(tech, list):
            parts.append(', '.join(tech[:4]))
        else:
            parts.append(tech[:30])
    return ' | '.join(parts) if parts else 'No content'

def get_section_configs_map(db: Session, user_id: uuid.UUID) -> Dict[str, Dict]:
    """Get section configs as a map keyed by type:key."""
    configs = db.query(SectionConfig).filter(
        SectionConfig.user_id == user_id
    ).all()
    
    return {
        f"{c.section_type}:{c.section_key}": {
            'priority': c.priority,
            'fixed_flavor': c.fixed_flavor
        }
        for c in configs
    }

def filter_by_priority(sections: Dict[str, List], configs: Dict[str, Dict]) -> Dict[str, List]:
    """Filter out sections with priority='never'."""
    filtered = {
        'experiences': [],
        'projects': [],
        'skills': []
    }
    
    for exp in sections['experiences']:
        config_key = f"experience:{exp['key']}"
        config = configs.get(config_key, {'priority': 'normal'})
        if config['priority'] != 'never':
            filtered['experiences'].append(exp)
    
    for proj in sections['projects']:
        config_key = f"project:{proj['key']}"
        config = configs.get(config_key, {'priority': 'normal'})
        if config['priority'] != 'never':
            filtered['projects'].append(proj)
    
    # Skills don't get filtered the same way
    filtered['skills'] = sections['skills']
    
    return filtered

def get_pinned_sections(sections: Dict[str, List], configs: Dict[str, Dict]) -> List[Dict]:
    """Get sections with priority='always'."""
    pinned = []
    
    for exp in sections['experiences']:
        config_key = f"experience:{exp['key']}"
        config = configs.get(config_key, {'priority': 'normal'})
        if config['priority'] == 'always':
            pinned.append({
                'type': 'experience',
                'key': exp['key'],
                'flavor': config['fixed_flavor']
            })
    
    for proj in sections['projects']:
        config_key = f"project:{proj['key']}"
        config = configs.get(config_key, {'priority': 'normal'})
        if config['priority'] == 'always':
            pinned.append({
                'type': 'project',
                'key': proj['key'],
                'flavor': config['fixed_flavor']
            })
    
    return pinned

def build_all_sections_response(sections: Dict[str, List], configs: Dict[str, Dict]) -> AllSections:
    """Build response object with all sections for UI."""
    experiences = []
    for exp in sections['experiences']:
        config_key = f"experience:{exp['key']}"
        config = configs.get(config_key, {'priority': 'normal', 'fixed_flavor': None})
        experiences.append(AllSectionInfo(
            key=exp['key'],
            flavors=[FlavorInfo(flavor=f['flavor'], version=f['version']) for f in exp['flavors']],
            priority=config['priority'],
            fixed_flavor=config.get('fixed_flavor')
        ))
    
    projects = []
    for proj in sections['projects']:
        config_key = f"project:{proj['key']}"
        config = configs.get(config_key, {'priority': 'normal', 'fixed_flavor': None})
        projects.append(AllSectionInfo(
            key=proj['key'],
            flavors=[FlavorInfo(flavor=f['flavor'], version=f['version']) for f in proj['flavors']],
            priority=config['priority'],
            fixed_flavor=config.get('fixed_flavor')
        ))
    
    skills = [
        SkillsInfo(flavor=s['flavor'], version=s['version'])
        for s in sections['skills']
    ]
    
    return AllSections(
        experiences=experiences,
        projects=projects,
        skills=skills
    )

def get_version_for_section(sections: Dict[str, List], section_type: str, key: str, flavor: str) -> str:
    """Look up version for a section."""
    type_key = 'experiences' if section_type == 'experience' else 'projects'
    for item in sections.get(type_key, []):
        if item['key'] == key:
            for f in item['flavors']:
                if f['flavor'] == flavor:
                    return f['version']
    return '1.0'

@router.post("/analyze", response_model=JDAnalyzeResponse)
async def analyze_jd(
    request: JDAnalyzeRequest,
    x_gemini_api_key: str = Header(..., alias="X-Gemini-API-Key"),
    user_id: uuid.UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Analyze JD with Gemini and return suggestions."""
    
    # Validate API key format
    if not x_gemini_api_key or len(x_gemini_api_key) < 20:
        raise HTTPException(status_code=400, detail="Invalid Gemini API key")
    
    # Fetch user's sections
    sections = get_user_sections(db, user_id)
    
    # Check if user has any content
    if not sections['experiences'] and not sections['projects'] and not sections['skills']:
        raise HTTPException(
            status_code=400, 
            detail="No content found. Please add sections to your Content Library first."
        )
    
    # Fetch section configs
    configs = get_section_configs_map(db, user_id)
    
    # Filter out 'never' priority sections
    filtered_sections = filter_by_priority(sections, configs)
    
    # Get pinned sections (priority='always')
    pinned_sections = get_pinned_sections(sections, configs)
    
    # Call Gemini
    try:
        result = await analyze_jd_with_gemini(
            api_key=x_gemini_api_key,
            job_description=request.job_description,
            additional_instructions=request.additional_instructions,
            sections=filtered_sections,
            pinned_sections=pinned_sections
        )
    except GeminiAuthError:
        raise HTTPException(status_code=401, detail="Invalid Gemini API key")
    except GeminiRateLimitError:
        raise HTTPException(status_code=429, detail="Gemini rate limit exceeded. Try again later.")
    except GeminiError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Build suggestions with versions
    experience_suggestions = []
    for exp in result.get('experiences', []):
        version = get_version_for_section(sections, 'experience', exp['key'], exp['flavor'])
        is_pinned = any(p['key'] == exp['key'] for p in pinned_sections)
        experience_suggestions.append(SectionSuggestion(
            key=exp['key'],
            flavor=exp['flavor'],
            version=version,
            pinned=is_pinned
        ))
    
    project_suggestions = []
    for proj in result.get('projects', []):
        version = get_version_for_section(sections, 'project', proj['key'], proj['flavor'])
        is_pinned = any(p['key'] == proj['key'] for p in pinned_sections)
        project_suggestions.append(SectionSuggestion(
            key=proj['key'],
            flavor=proj['flavor'],
            version=version,
            pinned=is_pinned
        ))
    
    suggestions = Suggestions(
        skills_flavor=result.get('skills_flavor', 'default'),
        experiences=experience_suggestions,
        projects=project_suggestions
    )
    
    # Build response
    return JDAnalyzeResponse(
        suggestions=suggestions,
        missing_keywords=result.get('missing_keywords', []),
        all_sections=build_all_sections_response(sections, configs)
    )

@router.post("/recalculate-keywords", response_model=KeywordRecalcResponse)
async def recalculate_keywords(
    request: KeywordRecalcRequest,
    x_gemini_api_key: str = Header(..., alias="X-Gemini-API-Key"),
    user_id: uuid.UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Recalculate missing keywords based on current selection using AI."""
    
    # Validate API key
    if not x_gemini_api_key or len(x_gemini_api_key) < 20:
        raise HTTPException(status_code=400, detail="Invalid Gemini API key")
    
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
            selected_content.append(edit.content.model_dump())
    
    # Convert to text for AI analysis
    resume_text = sections_to_text(selected_content)
    
    # Use AI to find missing keywords
    try:
        missing = await find_missing_keywords_with_ai(
            api_key=x_gemini_api_key,
            job_description=request.job_description,
            resume_content=resume_text
        )
    except KeywordServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return KeywordRecalcResponse(missing_keywords=missing)
