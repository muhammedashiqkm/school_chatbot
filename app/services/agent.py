from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.google_llm import Gemini
from app.services.tools import syllabus_tool
from app.config import settings
from app.instructions.agent_instructions import STUDENT_INSTRUCTIONS, TEACHER_INSTRUCTIONS

def get_agent(model_provider: str, user_type: str = "student") -> Agent:
    """
    Factory function to create an ADK Agent.
    Selects the system prompt based on 'user_type' (student/teacher).
    """
    
    model_wrapper = None
    
    if model_provider == "gemini":
        model_wrapper = Gemini(model=settings.GEMINI_MODEL_NAME)
    else:
        models_map = {
            "openai": f"openai/{settings.OPENAI_MODEL_NAME}",
            "deepseek": f"deepseek/{settings.DEEPSEEK_MODEL_NAME}",
        }
        target_model = models_map.get(model_provider)
        if not target_model:
            raise ValueError(f"Invalid model provider: {model_provider}")
        model_wrapper = LiteLlm(model=target_model)

    if user_type == "teacher":
        selected_instruction = TEACHER_INSTRUCTIONS
    else:
        selected_instruction = STUDENT_INSTRUCTIONS

    return Agent(
        model=model_wrapper,
        name="academic_tutor",
        instruction=selected_instruction,
        tools=[syllabus_tool]
    )