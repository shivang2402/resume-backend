"""
Gemini API Service - Reusable AI integration for Resume Forge.
Used by: Cold Outreach, JD Matcher
"""

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from fastapi import HTTPException
from typing import Optional, Dict, List, Any
import json
import re


class GeminiServiceError(Exception):
    """Base exception for Gemini service errors."""
    pass


class GeminiAPIKeyError(GeminiServiceError):
    """Raised when API key is invalid or missing."""
    pass


class GeminiRateLimitError(GeminiServiceError):
    """Raised when rate limit is exceeded."""
    pass


# Aliases for JD Matcher compatibility
GeminiError = GeminiServiceError
GeminiAuthError = GeminiAPIKeyError


class GeminiService:
    """
    Reusable Gemini Pro API client.
    
    Uses BYOK (Bring Your Own Key) model - API key passed per request.
    """
    
    DEFAULT_MODEL = "gemini-2.0-flash"
    
    def __init__(self, api_key: str):
        """Initialize Gemini client with user's API key."""
        if not api_key or not api_key.strip():
            raise GeminiAPIKeyError("Gemini API key is required")
        
        self.api_key = api_key.strip()
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.DEFAULT_MODEL)
    
    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> str:
        """
        Generate text using Gemini Pro.
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens in response
            temperature: Creativity (0.0-1.0)
            json_mode: If True, instruct model to return valid JSON
            
        Returns:
            Generated text string
            
        Raises:
            GeminiAPIKeyError: Invalid API key
            GeminiRateLimitError: Rate limit exceeded
            GeminiServiceError: Other API errors
        """
        try:
            generation_config = GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
            
            # Add JSON instruction if needed
            if json_mode:
                prompt = f"{prompt}\n\nRespond ONLY with valid JSON, no markdown formatting or extra text."
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Check for blocked content
            if not response.candidates:
                raise GeminiServiceError("Response was blocked by safety filters")
            
            return response.text.strip()
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "api key" in error_msg or "invalid" in error_msg or "401" in error_msg:
                raise GeminiAPIKeyError(f"Invalid Gemini API key: {e}")
            elif "rate" in error_msg or "quota" in error_msg or "429" in error_msg:
                raise GeminiRateLimitError(f"Rate limit exceeded. Please try again later: {e}")
            else:
                raise GeminiServiceError(f"Gemini API error: {e}")
    
    def generate_json(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.3
    ) -> dict:
        """
        Generate and parse JSON response.
        
        Args:
            prompt: The input prompt (should describe expected JSON structure)
            max_tokens: Maximum tokens
            temperature: Lower is more deterministic (good for JSON)
            
        Returns:
            Parsed JSON as dict
            
        Raises:
            GeminiServiceError: If JSON parsing fails
        """
        response = self.generate_text(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=True
        )
        
        # Clean response - remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise GeminiServiceError(f"Failed to parse JSON response: {e}\nResponse: {cleaned[:500]}")


def get_gemini_service(api_key: str) -> GeminiService:
    """
    Factory function to create GeminiService instance.
    
    Usage in endpoints:
        @router.post("/generate")
        def generate_message(
            data: GenerateRequest,
            gemini_api_key: str = Header(..., alias="X-Gemini-API-Key")
        ):
            gemini = get_gemini_service(gemini_api_key)
            result = gemini.generate_text(prompt)
    """
    return GeminiService(api_key)


def handle_gemini_error(e: Exception) -> HTTPException:
    """
    Convert Gemini exceptions to FastAPI HTTPExceptions.
    
    Usage:
        try:
            result = gemini.generate_text(prompt)
        except GeminiServiceError as e:
            raise handle_gemini_error(e)
    """
    if isinstance(e, GeminiAPIKeyError):
        return HTTPException(
            status_code=401,
            detail={"error": "invalid_api_key", "message": str(e)}
        )
    elif isinstance(e, GeminiRateLimitError):
        return HTTPException(
            status_code=429,
            detail={"error": "rate_limit", "message": str(e)}
        )
    else:
        return HTTPException(
            status_code=500,
            detail={"error": "ai_error", "message": str(e)}
        )


# ============================================
# JD Matcher Functions (async for analyze)
# ============================================

async def analyze_jd_with_gemini(
    api_key: str,
    job_description: str,
    additional_instructions: Optional[str],
    sections: Dict[str, List],
    pinned_sections: List[Dict]
) -> Dict[str, Any]:
    """
    Call Gemini to analyze JD against user's sections.
    Returns suggestions and missing keywords.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = build_analysis_prompt(
        job_description,
        additional_instructions,
        sections,
        pinned_sections
    )
    
    try:
        response = await model.generate_content_async(prompt)
        result = parse_gemini_response(response.text)
        return result
    except Exception as e:
        error_msg = str(e).lower()
        if "api key" in error_msg or "authentication" in error_msg or "api_key" in error_msg:
            raise GeminiAuthError("Invalid API key")
        elif "quota" in error_msg or "rate" in error_msg or "resource" in error_msg:
            raise GeminiRateLimitError("Rate limit exceeded")
        else:
            raise GeminiError(f"Gemini error: {str(e)}")


def build_analysis_prompt(
    job_description: str,
    additional_instructions: Optional[str],
    sections: Dict[str, List],
    pinned_sections: List[Dict]
) -> str:
    """Build the Gemini prompt for JD analysis."""
    
    prompt = f"""You are a resume optimization assistant.
I have a job description and resume sections with different "flavors" (variations).
Analyze the JD and suggest which sections/flavors to include.

**Job Description:**
{job_description}

"""
    
    if additional_instructions:
        prompt += f"""**Additional Instructions:**
{additional_instructions}

"""
    
    if pinned_sections:
        prompt += "**Required Sections (must include):**\n"
        for ps in pinned_sections:
            prompt += f"- {ps['type'].title()}: {ps['key']} (flavor: {ps['flavor']})\n"
        prompt += "\n"
    
    prompt += "**Available Sections:**\n\n"
    
    # Experiences
    prompt += "EXPERIENCES:\n"
    for exp in sections.get('experiences', []):
        prompt += f"- Key: {exp['key']}\n"
        for flavor_info in exp['flavors']:
            prompt += f"  - Flavor '{flavor_info['flavor']}' (v{flavor_info['version']}):\n"
            prompt += f"    {flavor_info['content_summary']}\n"
    
    # Projects
    prompt += "\nPROJECTS:\n"
    for proj in sections.get('projects', []):
        prompt += f"- Key: {proj['key']}\n"
        for flavor_info in proj['flavors']:
            prompt += f"  - Flavor '{flavor_info['flavor']}' (v{flavor_info['version']}):\n"
            prompt += f"    {flavor_info['content_summary']}\n"
    
    # Skills
    prompt += "\nSKILLS FLAVORS:\n"
    for skill in sections.get('skills', []):
        prompt += f"- Flavor '{skill['flavor']}' (v{skill['version']}): {skill['content_summary']}\n"
    
    prompt += """
**Instructions:**
1. Select 2-4 experiences that best match this JD (plus any required sections)
2. Select 2-3 projects that best match this JD
3. Select the best skills flavor
4. For each section, pick the most relevant flavor
5. List important keywords from the JD that are NOT in the selected sections

**Respond in this exact JSON format (no markdown, no explanation):**
{
  "skills_flavor": "string",
  "experiences": [
    {"key": "string", "flavor": "string"}
  ],
  "projects": [
    {"key": "string", "flavor": "string"}
  ],
  "missing_keywords": ["string", "string"]
}
"""
    
    return prompt


def parse_gemini_response(response_text: str) -> Dict[str, Any]:
    """Parse Gemini response, extracting JSON."""
    
    # Try to find JSON in response
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    
    if not json_match:
        raise GeminiError("No JSON found in response")
    
    try:
        result = json.loads(json_match.group())
        
        # Validate structure
        required_keys = ['skills_flavor', 'experiences', 'projects', 'missing_keywords']
        for key in required_keys:
            if key not in result:
                raise GeminiError(f"Missing key in response: {key}")
        
        return result
    except json.JSONDecodeError as e:
        raise GeminiError(f"Invalid JSON in response: {str(e)}")
