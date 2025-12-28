from pydantic import BaseModel, Field
from typing import Optional, Literal, List

class ChatRequest(BaseModel):
    chatbot_user_id: str = Field(..., description="Unique ID for the user session")
    question: str
    
    syllabus: str
    class_name: str
    subject: str
    school: Optional[str] = None

    model: Literal["gemini", "openai", "deepseek"] = "gemini"

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []

class ClearSessionRequest(BaseModel):
    chatbot_user_id: str