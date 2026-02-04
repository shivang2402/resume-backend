"""
Gemini API Service - Reusable AI integration for Resume Forge.
Used by: Cold Outreach, JD Matcher
"""

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from fastapi import HTTPException
from typing import Optional
import json


class GeminiServiceError(Exception):
    """Base exception for Gemini service errors."""
    pass


class GeminiAPIKeyError(GeminiServiceError):
    """Raised when API key is invalid or missing."""
    pass


class GeminiRateLimitError(GeminiServiceError):
    """Raised when rate limit is exceeded."""
    pass


class GeminiService:
    """
    Reusable Gemini Pro API client.
    
    Uses BYOK (Bring Your Own Key) model - API key passed per request.
    """
    
    DEFAULT_MODEL = "gemini-2.5-flash"
    
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