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
        return _parse_match_response(response.text)
    except Exception as e:
        print(f"Matching failed: {e}")
        return {
            "experiences": [],
            "projects": [],
            "skills_flavor": "default",
            "missing_keywords": [],
        }


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
1. Select 2-4 best matching experiences
2. Select 2-3 best matching projects  
3. Select best skills flavor
4. List important JD terms NOT covered by selected sections
5. For each selection, explain WHY it matches

Return ONLY this JSON:
{
  "experiences": [
    {"key": "...", "flavor": "...", "reason": "matches X, Y, Z"}
  ],
  "projects": [
    {"key": "...", "flavor": "...", "reason": "matches X, Y"}
  ],
  "skills_flavor": "...",
  "missing_keywords": ["term1", "term2"]
}

JSON:"""
    
    return prompt


def _parse_match_response(response_text: str) -> Dict[str, Any]:
    """Parse matching response."""
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    return {
        "experiences": [],
        "projects": [],
        "skills_flavor": "default",
        "missing_keywords": []
    }
