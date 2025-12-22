from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.google_llm import Gemini
from app.services.tools import syllabus_tool
from app.config import settings
from app.agents.instructions import SYLLABUS_AGENT_INSTRUCTIONS

def get_agent(model_provider: str) -> Agent:
    """Factory function to create an ADK Agent based on the provider."""
    
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

    return Agent(
        model=model_wrapper,
        name="academic_tutor",
        instruction="You are a helpful academic tutor. Use the 'search_syllabus' tool to find specific information.",
        tools=[syllabus_tool]
    )