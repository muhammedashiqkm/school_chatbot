from pydantic import BaseModel, Field
from typing import List

class SchoolSetupRequest(BaseModel):
    """
    Schema for initializing a school's structure.
    Uses 'alias' to map the reserved keyword 'class' from JSON to 'class_' in Python.
    """
    school_name: str
    syllabus: List[str]
    class_: List[str] = Field(..., alias="class") 
    subject: List[str]

    class Config:
        populate_by_name = True 

class SchoolResponse(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True