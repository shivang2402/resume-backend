import google.generativeai as genai
import json
import re
from typing import List, Set, Dict, Any

class KeywordServiceError(Exception):
    pass

async def extract_keywords_with_ai(api_key: str, text: str) -> List[str]:
    """Use Gemini to extract technical keywords from text."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""Extract all technical keywords, skills, tools, and technologies from this text.
Include: programming languages, frameworks, libraries, databases, cloud services, 
methodologies, tools, concepts, certifications, and domain-specific terms.

Text:
{text}

Return ONLY a JSON array of lowercase keywords, nothing else. Example:
["python", "aws", "kubernetes", "machine learning"]
"""
    
    try:
        response = await model.generate_content_async(prompt)
        # Parse JSON from response
        json_match = re.search(r'\[[\s\S]*\]', response.text)
        if json_match:
            keywords = json.loads(json_match.group())
            return [k.lower().strip() for k in keywords if isinstance(k, str)]
        return []
    except Exception as e:
        raise KeywordServiceError(f"Failed to extract keywords: {str(e)}")

async def find_missing_keywords_with_ai(
    api_key: str,
    job_description: str,
    resume_content: str
) -> List[str]:
    """Use Gemini to find JD keywords missing from resume."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""Compare this job description with the resume content.
Identify important technical keywords, skills, and requirements from the JD 
that are NOT present in the resume content.

Focus on: programming languages, frameworks, tools, technologies, methodologies,
certifications, and domain-specific terms that would be valuable to add.

JOB DESCRIPTION:
{job_description}

RESUME CONTENT:
{resume_content}

Return ONLY a JSON array of the missing keywords (lowercase), nothing else.
Limit to the 10-15 most important missing keywords.
Example: ["kubernetes", "terraform", "ci/cd"]
"""
    
    try:
        response = await model.generate_content_async(prompt)
        json_match = re.search(r'\[[\s\S]*\]', response.text)
        if json_match:
            keywords = json.loads(json_match.group())
            return [k.lower().strip() for k in keywords if isinstance(k, str)]
        return []
    except Exception as e:
        raise KeywordServiceError(f"Failed to find missing keywords: {str(e)}")

def content_to_text(content: Dict[str, Any]) -> str:
    """Convert section content dict to searchable text."""
    parts = []
    
    if 'title' in content:
        parts.append(str(content['title']))
    if 'company' in content:
        parts.append(str(content['company']))
    if 'bullets' in content:
        parts.extend([str(b) for b in content['bullets']])
    if 'skills' in content:
        if isinstance(content['skills'], list):
            parts.extend([str(s) for s in content['skills']])
        elif isinstance(content['skills'], dict):
            for category, skills in content['skills'].items():
                parts.append(str(category))
                if isinstance(skills, list):
                    parts.extend([str(s) for s in skills])
    if 'description' in content:
        parts.append(str(content['description']))
    
    return ' '.join(parts)

def sections_to_text(section_contents: List[Dict[str, Any]]) -> str:
    """Convert multiple section contents to combined text."""
    return '\n\n'.join(content_to_text(c) for c in section_contents)
