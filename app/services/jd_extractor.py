"""
JD Extractor - AI extracts important terms from job descriptions.
Removes fluff, preserves critical info like sponsorship.
"""

import google.generativeai as genai
import json
import re
from typing import Dict, List, Any


async def extract_jd_terms(api_key: str, job_description: str) -> Dict[str, Any]:
    """
    Use AI to extract all important terms from a JD.
    
    Returns dict with:
        - terms: List of important keywords
        - sponsorship: 'yes', 'no', or 'unknown'
        - years_experience: str or None
        - location: str or None
        - remote: 'remote', 'hybrid', 'onsite', or 'unknown'
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""Extract important information from this job description.

REMOVE: Company description, benefits, EEO statements, culture/values, "about us", "why join us"

EXTRACT:
1. All technical skills required (languages, frameworks, tools, databases, cloud)
2. Soft skills mentioned (leadership, communication, etc.)
3. Years of experience required
4. Visa/sponsorship status (look for "sponsorship", "visa", "authorized to work", "citizenship")
5. Location and remote policy
6. Any must-have requirements

Job Description:
{job_description}

Return ONLY this JSON format:
{{
  "terms": ["python", "aws", "leadership", "5+ years", ...],
  "sponsorship": "yes" | "no" | "unknown",
  "years_experience": "5+" | null,
  "location": "Seattle, WA" | null,
  "remote": "remote" | "hybrid" | "onsite" | "unknown"
}}

JSON:"""

    try:
        response = await model.generate_content_async(prompt)
        return _parse_jd_response(response.text)
    except Exception as e:
        print(f"JD extraction failed: {e}")
        return {
            "terms": [],
            "sponsorship": "unknown",
            "years_experience": None,
            "location": None,
            "remote": "unknown"
        }


def _parse_jd_response(response_text: str) -> Dict[str, Any]:
    """Parse AI response to extract JD info."""
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    
    if json_match:
        try:
            result = json.loads(json_match.group())
            if 'terms' in result:
                result['terms'] = [str(t).lower().strip() for t in result['terms']]
            return result
        except json.JSONDecodeError:
            pass
    
    return {
        "terms": [],
        "sponsorship": "unknown",
        "years_experience": None,
        "location": None,
        "remote": "unknown"
    }
