from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class DocumentUrlRequest(BaseModel):
    url: str
    display_name: str
    school: str
    syllabus: str
    class_name: str
    subject: str

    @validator('url')
    def empty_str_to_none(cls, v):
        return v if v else ""

class DocumentListRequest(BaseModel):
    college: Optional[str] = None
    syllabus: Optional[str] = None
    class_name: Optional[str] = None
    subject: Optional[str] = None

class SubjectSearchRequest(BaseModel):
    school: str
    syllabus: str
    class_name: str

class DocumentResponse(BaseModel):
    id: UUID 
    display_name: str
    source_url: Optional[str] = None
    school_name: str
    syllabus: str
    class_name: str
    subject: str
    status: str
    error: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True