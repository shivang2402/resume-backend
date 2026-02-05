"""
Tag Generator - AI extracts tags from resume sections.
Called once on section create/edit, stored in content.tags
"""

import google.generativeai as genai
import json
import re
from typing import Dict, List, Any


async def generate_section_tags(api_key: str, content: Dict[str, Any], section_type: str) -> List[str]:
    """
    Use AI to extract all important tags from a section.
    Tags include: tech skills, soft skills, impact keywords.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    content_text = _content_to_text(content)
    
    prompt = f"""Extract ALL important keywords/tags from this resume {section_type} section.

Include:
- Technical skills (languages, frameworks, tools, databases, cloud services)
- Soft skills (leadership, communication, collaboration, mentoring)
- Impact keywords (scaled, optimized, reduced, improved, built, designed, led)
- Domain terms (distributed systems, microservices, ML, etc.)
- Metrics indicators (%, numbers, scale like "1M users", "150k nodes")

Section content:
{content_text}

Return ONLY a JSON array of lowercase tags. No explanation.
Example: ["python", "aws", "leadership", "reduced latency 40%", "microservices"]

Tags:"""

    try:
        response = await model.generate_content_async(prompt)
        return _parse_tags_response(response.text)
    except Exception as e:
        print(f"Tag generation failed: {e}")
        return []


def _content_to_text(content: Dict[str, Any]) -> str:
    """Convert section content to text for AI processing."""
    parts = []
    
    if 'title' in content:
        parts.append(f"Title: {content['title']}")
    if 'role' in content:
        parts.append(f"Role: {content['role']}")
    if 'company' in content:
        parts.append(f"Company: {content['company']}")
    if 'name' in content:
        parts.append(f"Project: {content['name']}")
    if 'bullets' in content:
        parts.append("Bullets:")
        for bullet in content['bullets']:
            parts.append(f"- {bullet}")
    if 'tech_stack' in content:
        parts.append(f"Tech Stack: {', '.join(content['tech_stack'])}")
    if 'skills' in content:
        if isinstance(content['skills'], dict):
            for category, skills in content['skills'].items():
                parts.append(f"{category}: {', '.join(skills)}")
        elif isinstance(content['skills'], list):
            parts.append(f"Skills: {', '.join(content['skills'])}")
    
    return '\n'.join(parts)


def _parse_tags_response(response_text: str) -> List[str]:
    """Parse AI response to extract tags array."""
    json_match = re.search(r'\[[\s\S]*?\]', response_text)
    
    if json_match:
        try:
            tags = json.loads(json_match.group())
            return [str(tag).lower().strip() for tag in tags if tag]
        except json.JSONDecodeError:
            pass
    
    return []
