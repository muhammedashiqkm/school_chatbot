from pydantic import BaseModel, Field
from typing import Optional, Literal, List

class ChatRequest(BaseModel):
    chatbot_user_id: str = Field(..., description="Unique ID for the user session")
    question: str
    college: str = Field(..., description="Name of the College")
    syllabus: str
    class_name: str
    subject: str
    user_type: Literal["student", "teacher"] = "student"
    model: Literal["gemini", "openai", "deepseek"] = "gemini"

class ChatResponse(BaseModel):
    answer: str

class ClearSessionRequest(BaseModel):
    chatbot_user_id: str