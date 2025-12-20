from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from typing import Optional

class DocumentResponse(BaseModel):
    id: UUID4
    display_name: Optional[str] = None
    source_url: Optional[str] = None
    status: str
    error: Optional[str] = None
    school_name: str
    syllabus: str
    class_name: str
    subject: str
    created_at: datetime

    class Config:
        from_attributes = True 

class DocumentUrlRequest(BaseModel):
    url: str
    display_name: Optional[str] = None
    
    school: str
    syllabus: str
    class_name: str
    subject: str