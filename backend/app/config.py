import os
from dotenv import load_dotenv

# Load env vars from .env file
load_dotenv()

class Settings:
    # API Keys for Rotation
    GEMINI_API_KEY_1 = os.environ.get("GEMINI_API_KEY_1")
    GEMINI_API_KEY_2 = os.environ.get("GEMINI_API_KEY_2")
    GEMINI_API_KEY_3 = os.environ.get("GEMINI_API_KEY_3")
    
    # Models
    RERANK_MODEL = os.environ.get("RERANK_MODEL")
    EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL")
    # Using REWRITE_MODEL as noted in query_rewriter.py
    REWRITE_MODEL = os.environ.get("REWRITE_MODEL") 

    @classmethod
    def validate(cls):
        """
        Enforce strict environment variable presence.
        Fails fast at startup if critical keys are missing.
        """
        missing = []
        if not cls.GEMINI_API_KEY_1: missing.append("GEMINI_API_KEY_1")
        if not cls.GEMINI_API_KEY_2: missing.append("GEMINI_API_KEY_2")
        if not cls.GEMINI_API_KEY_3: missing.append("GEMINI_API_KEY_3")
        
        if not cls.RERANK_MODEL: missing.append("RERANK_MODEL")
        if not cls.EMBEDDING_MODEL: missing.append("EMBEDDING_MODEL")
        if not cls.REWRITE_MODEL: missing.append("REWRITE_MODEL")

        if missing:
            raise ValueError(f"CRITICAL: Missing required environment variables: {', '.join(missing)}")

# Validate on import
Settings.validate()
