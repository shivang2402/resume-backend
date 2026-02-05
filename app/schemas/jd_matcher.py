from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class JDAnalyzeRequest(BaseModel):
    job_description: str
    additional_instructions: Optional[str] = None

class SectionSuggestion(BaseModel):
    key: str
    flavor: str
    version: str
    pinned: bool = False

class Suggestions(BaseModel):
    skills_flavor: str
    experiences: List[SectionSuggestion]
    projects: List[SectionSuggestion]

class FlavorInfo(BaseModel):
    flavor: str
    version: str

class AllSectionInfo(BaseModel):
    key: str
    flavors: List[FlavorInfo]
    priority: str
    fixed_flavor: Optional[str] = None

class SkillsInfo(BaseModel):
    flavor: str
    version: str

class AllSections(BaseModel):
    experiences: List[AllSectionInfo]
    projects: List[AllSectionInfo]
    skills: List[SkillsInfo]

class JDAnalyzeResponse(BaseModel):
    suggestions: Suggestions
    missing_keywords: List[str]
    all_sections: AllSections

class SelectedSection(BaseModel):
    type: str
    key: str
    flavor: str
    version: str

class TempEditContent(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    dates: Optional[str] = None
    bullets: List[str] = []

class TempEdit(BaseModel):
    content: TempEditContent

class KeywordRecalcRequest(BaseModel):
    job_description: str
    selected_sections: List[SelectedSection]
    temp_edits: Optional[Dict[str, TempEdit]] = {}

class KeywordRecalcResponse(BaseModel):
    missing_keywords: List[str]
