from pydantic import BaseModel, Field
from typing import List

class SchoolSetupRequest(BaseModel):
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