"""
JD Matcher Service - Matches JD terms against section tags.
Uses pre-computed tags for efficiency.
"""

import google.generativeai as genai
import json
import re
from typing import Dict, List, Any


async def match_sections_to_jd(
    api_key: str,
    jd_terms: List[str],
    jd_info: Dict[str, Any],
    sections_with_tags: Dict[str, List[Dict]],
    pinned_sections: List[Dict]
) -> Dict[str, Any]:
    """
    Match section tags against JD terms.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = _build_match_prompt(jd_terms, jd_info, sections_with_tags, pinned_sections)
    
    try:
        response = await model.generate_content_async(prompt)
        result = _parse_match_response(response.text)
        
        # Ensure we always return results if sections exist
        result = _ensure_results(result, sections_with_tags, pinned_sections)
        
        return result
    except Exception as e:
        print(f"Matching failed: {e}")
        raise  # Re-raise for router to handle


def _build_match_prompt(
    jd_terms: List[str],
    jd_info: Dict[str, Any],
    sections_with_tags: Dict[str, List[Dict]],
    pinned_sections: List[Dict]
) -> str:
    """Build compact matching prompt."""
    
    prompt = f"""Match resume sections to job requirements.

JOB REQUIREMENTS:
Terms: {', '.join(jd_terms[:30])}
Experience: {jd_info.get('years_experience') or 'Not specified'}
Sponsorship: {jd_info.get('sponsorship', 'unknown')}
Remote: {jd_info.get('remote', 'unknown')}

"""
    
    if pinned_sections:
        prompt += "MUST INCLUDE:\n"
        for p in pinned_sections:
            prompt += f"- {p['key']}:{p['flavor']}\n"
        prompt += "\n"
    
    prompt += "AVAILABLE SECTIONS:\n\nExperiences:\n"
    for exp in sections_with_tags.get('experiences', []):
        for flavor in exp.get('flavors', []):
            tags = flavor.get('tags', [])
            prompt += f"- {exp['key']}:{flavor['flavor']} [{', '.join(tags[:15])}]\n"
    
    prompt += "\nProjects:\n"
    for proj in sections_with_tags.get('projects', []):
        for flavor in proj.get('flavors', []):
            tags = flavor.get('tags', [])
            prompt += f"- {proj['key']}:{flavor['flavor']} [{', '.join(tags[:15])}]\n"
    
    prompt += "\nSkills Flavors:\n"
    for skill in sections_with_tags.get('skills', []):
        tags = skill.get('tags', [])
        prompt += f"- {skill['flavor']} [{', '.join(tags[:15])}]\n"
    
    prompt += """
TASK:
1. Select 2-4 best matching experiences (MUST select at least 2 if available, even if match is weak)
2. Select 2-3 best matching projects (MUST select at least 2 if available, even if match is weak)
3. Select best skills flavor (MUST select one if available)
4. List important JD terms NOT covered by selected sections
5. For each selection, explain WHY it matches (or say "closest available" if weak match)

IMPORTANT: 
- Always return the closest matching sections. Never return empty arrays if sections are available.
- The "key" and "flavor" must be SEPARATE fields, exactly as shown in AVAILABLE SECTIONS above.
- Format: key is BEFORE the colon, flavor is AFTER the colon (e.g., "tesla:mechanical" means key="tesla", flavor="mechanical")

Return ONLY this JSON (no markdown, no extra text):
{
  "experiences": [
    {"key": "tesla", "flavor": "mechanical", "reason": "matches X, Y, Z"}
  ],
  "projects": [
    {"key": "battery_management", "flavor": "electrical", "reason": "matches X, Y"}
  ],
  "skills_flavor": "systems",
  "missing_keywords": ["term1", "term2"]
}

JSON:"""
    
    return prompt


def _parse_match_response(response_text: str) -> Dict[str, Any]:
    """Parse matching response."""
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    
    if json_match:
        try:
            result = json.loads(json_match.group())
            
            # Fix malformed key:flavor combinations
            for exp in result.get('experiences', []):
                if ':' in exp.get('key', ''):
                    parts = exp['key'].split(':')
                    exp['key'] = parts[0]
                    if len(parts) > 1 and (not exp.get('flavor') or ':' in exp.get('flavor', '')):
                        exp['flavor'] = parts[1]
                # Clean flavor if it contains brackets or extra text
                if exp.get('flavor'):
                    exp['flavor'] = exp['flavor'].split('[')[0].split(':')[-1].strip()
            
            for proj in result.get('projects', []):
                if ':' in proj.get('key', ''):
                    parts = proj['key'].split(':')
                    proj['key'] = parts[0]
                    if len(parts) > 1 and (not proj.get('flavor') or ':' in proj.get('flavor', '')):
                        proj['flavor'] = parts[1]
                # Clean flavor if it contains brackets or extra text
                if proj.get('flavor'):
                    proj['flavor'] = proj['flavor'].split('[')[0].split(':')[-1].strip()
            
            return result
        except json.JSONDecodeError:
            pass
    
    return {
        "experiences": [],
        "projects": [],
        "skills_flavor": "default",
        "missing_keywords": []
    }


def _ensure_results(
    result: Dict[str, Any],
    sections_with_tags: Dict[str, List[Dict]],
    pinned_sections: List[Dict]
) -> Dict[str, Any]:
    """Ensure we always return results if sections are available."""
    
    experiences = sections_with_tags.get('experiences', [])
    projects = sections_with_tags.get('projects', [])
    skills = sections_with_tags.get('skills', [])
    
    # If no experiences returned but we have some, add closest ones
    if not result.get('experiences') and experiences:
        result['experiences'] = []
        for exp in experiences[:3]:
            flavors = exp.get('flavors', [])
            if flavors:
                result['experiences'].append({
                    'key': exp['key'],
                    'flavor': flavors[0]['flavor'],
                    'reason': 'closest available match'
                })
    
    # If no projects returned but we have some, add closest ones
    if not result.get('projects') and projects:
        result['projects'] = []
        for proj in projects[:2]:
            flavors = proj.get('flavors', [])
            if flavors:
                result['projects'].append({
                    'key': proj['key'],
                    'flavor': flavors[0]['flavor'],
                    'reason': 'closest available match'
                })
    
    # If no skills flavor but we have some, pick first
    if (not result.get('skills_flavor') or result.get('skills_flavor') == 'default') and skills:
        result['skills_flavor'] = skills[0]['flavor']
    
    # Ensure pinned sections are included
    for pinned in pinned_sections:
        section_type = pinned['type']
        key = pinned['key']
        flavor = pinned.get('flavor')
        
        list_key = 'experiences' if section_type == 'experience' else 'projects'
        
        # Check if already in results
        already_included = any(
            s['key'] == key for s in result.get(list_key, [])
        )
        
        if not already_included:
            # Find the flavor from available sections
            if not flavor:
                for section in sections_with_tags.get(list_key, []):
                    if section['key'] == key and section.get('flavors'):
                        flavor = section['flavors'][0]['flavor']
                        break
            
            if flavor:
                result[list_key] = result.get(list_key, [])
                result[list_key].insert(0, {
                    'key': key,
                    'flavor': flavor,
                    'reason': 'pinned section'
                })
    
    return result