# backend/app/key_manager.py
"""
Simple API Key Manager for rotating Gemini API keys.
Designed for single-user/low-traffic scenarios.
"""
import time
from google import genai
from app.config import Settings

class KeyManager:
    """Simple key rotation manager - rotates after each call."""
    
    _instance = None  # Singleton
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Load keys from Settings (Strictly validated already)
        self.keys = [
            Settings.GEMINI_API_KEY_1,
            Settings.GEMINI_API_KEY_2,
            Settings.GEMINI_API_KEY_3
        ]
        
        print(f"🔑 KeyManager: Loaded {len(self.keys)} API keys for rotation.")
        self.clients = [genai.Client(api_key=k) for k in self.keys]
        self.current_idx = 0
        self._initialized = True

    def get_client(self):
        """Get current client without rotating."""
        return self.clients[self.current_idx]

    def get_client_and_rotate(self):
        """Get current client and rotate to next for next call."""
        client = self.clients[self.current_idx]
        old_idx = self.current_idx
        self.current_idx = (self.current_idx + 1) % len(self.clients)
        print(f"🔄 Using key {old_idx}, next will be {self.current_idx}")
        return client


# Singleton accessor
_key_manager = None

def get_key_manager() -> KeyManager:
    """Get or create the singleton KeyManager instance."""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


# Rate limiting helper
def rate_limit_sleep(seconds: float = 5.0):
    """Sleep to respect API rate limits."""
    print(f"⏳ Rate limit sleep: {seconds}s...")
    time.sleep(seconds)
