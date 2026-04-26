"""
Resume PDF parser.

Pipeline: pdfplumber extracts layout-aware text from a PDF, then Gemini
turns that text into a list of section *suggestions*. Flavor and final
content remain user-owned — the model never picks a flavor.
"""

import io
from typing import Any

import pdfplumber

from app.services.gemini_service import GeminiService


PARSE_PROMPT = """You are a resume parser. Convert the resume text below into a JSON array of section suggestions.

Allowed `type` values: experience, project, skills, coursework, education, heading.

For each section, output:
{
  "type": "<one of the allowed types>",
  "suggested_key": "<short slug, lowercase, underscores, e.g. amazon, my_project, ms_cs>",
  "content": { /* section-specific fields, see below */ },
  "confidence": "high" | "low"
}

Content shape per type:
- experience: { "title", "company", "location", "dates", "bullets": [..] }
- project:    { "name", "tech", "dates", "bullets": [..] }
- education:  { "degree", "institution", "location", "dates", "gpa" (optional) }
- skills:     { "groups": [{ "label", "items": [..] }] }   // e.g. label "Languages", items ["Python","Go"]
- coursework: { "items": [..] }
- heading:    { "name", "email", "phone", "links": [..] }

Rules:
- Do NOT invent content. If a field isn't in the text, omit it.
- Keep bullets verbatim; do not summarize.
- Set confidence "low" if you guessed the section type or the text was ambiguous.
- Return ONLY a JSON array. No prose, no markdown fences.

Resume text:
---
{resume_text}
---
"""


def extract_text(file_bytes: bytes) -> str:
    """Extract resume text in reading order using pdfplumber word positions."""
    lines: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=["size", "fontname"]) or []
            words.sort(key=lambda w: (round(float(w["top"]), 1), float(w["x0"])))
            current_top: float | None = None
            current_line: list[str] = []
            for w in words:
                top = round(float(w["top"]), 1)
                if current_top is None or abs(top - current_top) > 3:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [w["text"]]
                    current_top = top
                else:
                    current_line.append(w["text"])
            if current_line:
                lines.append(" ".join(current_line))
            lines.append("")  # page break
    return "\n".join(lines).strip()


def parse_resume_pdf(file_bytes: bytes, gemini: GeminiService) -> list[dict[str, Any]]:
    """
    Returns a list of section suggestions. Caller is expected to surface
    these to the user for review (especially flavor selection) before
    persisting via /api/sections/bulk.
    """
    text = extract_text(file_bytes)
    if not text:
        return []

    prompt = PARSE_PROMPT.replace("{resume_text}", text[:12000])
    raw = gemini.generate_text(prompt, max_tokens=4096, temperature=0.2, json_mode=True)

    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    import json
    parsed = json.loads(cleaned.strip())
    if not isinstance(parsed, list):
        return []
    return parsed
