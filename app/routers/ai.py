"""
AI Router - Test endpoint for Gemini integration.
Can be removed in production or kept for debugging.
"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.gemini_service import (
    get_gemini_service,
    handle_gemini_error,
    GeminiServiceError
)


router = APIRouter()


class TestGenerateRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.7


class TestGenerateResponse(BaseModel):
    success: bool
    response: str
    model: str


@router.post("/test", response_model=TestGenerateResponse)
def test_gemini_connection(
    data: TestGenerateRequest,
    x_gemini_api_key: str = Header(..., alias="X-Gemini-API-Key")
):
    """
    Test Gemini API connection with user's API key.
    
    Headers:
        X-Gemini-API-Key: User's Gemini API key
        
    Returns success status and generated response.
    """
    try:
        gemini = get_gemini_service(x_gemini_api_key)
        
        response = gemini.generate_text(
            prompt=data.prompt,
            max_tokens=data.max_tokens,
            temperature=data.temperature
        )
        
        return TestGenerateResponse(
            success=True,
            response=response,
            model=gemini.DEFAULT_MODEL
        )
        
    except GeminiServiceError as e:
        raise handle_gemini_error(e)


@router.get("/health")
def ai_health_check():
    """Check if AI router is loaded (doesn't test API key)."""
    return {
        "status": "healthy",
        "service": "gemini",
        "model": "gemini-1.5-flash"
    }
