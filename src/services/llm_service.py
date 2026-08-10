from langchain_openai import ChatOpenAI
from ..config.settings import settings


class LLMService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.api_key,
            base_url=settings.base_url
        )
        self.llm_json = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.api_key,
            base_url=settings.base_url,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
    
    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
    
    def generate_json(self, prompt: str) -> str:
        response = self.llm_json.invoke(prompt)
        return response.content
