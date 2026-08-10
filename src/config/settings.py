import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    
    @staticmethod
    def _norm(value: str | None) -> str:
        if value is None:
            return ""
        return value.strip().strip('"').strip("'")

    # Support both LLM_KEY and OPENAI_API_KEY for backwards compatibility
    LLM_KEY: str = _norm.__func__(os.getenv("LLM_KEY")) or _norm.__func__(os.getenv("OPENAI_API_KEY"))
    LLM_BASE_URL: str = _norm.__func__(os.getenv("LLM_BASE_URL"))
    LLM_MODEL: str = _norm.__func__(os.getenv("LLM_MODEL"))
    LLM_TEMPERATURE: float = float(_norm.__func__(os.getenv("LLM_TEMPERATURE")))
    
    EMBEDDING_KEY: str = _norm.__func__(os.getenv("EMBEDDING_KEY"))
    EMBEDDING_MODEL: str = _norm.__func__(os.getenv("EMBEDDING_MODEL")) or "text-embedding-3-small"
    
    QDRANT_URL: str = _norm.__func__(os.getenv("QDRANT_URL")) or "http://localhost:6333"
    QDRANT_API_KEY: str = _norm.__func__(os.getenv("QDRANT_API_KEY"))
    QDRANT_COLLECTION: str = _norm.__func__(os.getenv("QDRANT_COLLECTION")) or "sql_queries"
    
    GOOGLE_API_KEY: str = _norm.__func__(os.getenv("GOOGLE_API_KEY"))
    GOOGLE_SEARCH_ENGINE_ID: str = _norm.__func__(os.getenv("GOOGLE_SEARCH_ENGINE_ID"))
    SCHEMA_WORD_THRESHOLD: int = int(_norm.__func__(os.getenv("SCHEMA_WORD_THRESHOLD")) or "5000")
    
    @property
    def api_key(self) -> str:
        return self.LLM_KEY
    
    @property
    def base_url(self) -> str:
        if self.LLM_BASE_URL:
            return self.LLM_BASE_URL


        
        model_lower = self.LLM_MODEL.lower()
        if "deepseek" in model_lower:
            return "https://api.deepseek.com/v1"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "https://api.openai.com/v1"
        elif "claude" in model_lower:
            return "https://api.anthropic.com"
        elif "gemini" in model_lower:
            return "https://generativelanguage.googleapis.com"
        
        return None

settings = Settings()

