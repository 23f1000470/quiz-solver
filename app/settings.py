import os
from pydantic_settings import BaseSettings
from typing import Optional, Dict
import json

class Settings(BaseSettings):
    # API Configuration
    APP_NAME: str = "Quiz Solver API"
    DEBUG: bool = False
    
    GEMINI_API_KEY: str
    
    # CORRECT model configuration based on your available models
    # Use cheaper models first to avoid rate limits
    GEMINI_MODEL_PRIMARY: str = "gemini-2.0-flash-lite"  # Fast and cheap for first attempt
    GEMINI_MODEL_FALLBACKS: list = [
        "gemini-2.0-flash",      # Balanced for second attempt
        "gemini-2.5-flash",      # Smarter for third attempt
        "gemini-2.5-pro",        # Most capable for final attempt
    ]
    
    # Retry configuration
    MAX_QUIZ_ATTEMPTS: int = 3  # Max attempts per quiz question
    RETRY_DELAY: float = 2.0    # Delay between retries in seconds
    
    # AIPipe Configuration (fallback)
    AIPIPE_API_KEY: Optional[str] = None
    
    # Playwright Configuration
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 30000
    
    # Solver Configuration
    MAX_ATTEMPTS: int = 3
    TOTAL_TIMEOUT: int = 180
    REQUEST_TIMEOUT: int = 30
    
    # User validation secrets - CRITICAL: Load from environment variables
    STUDENT_EMAIL: str
    STUDENT_SECRET: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # This ignores extra environment variables

    def validate_user_secret(self, email: str, secret: str) -> bool:
        """Validate user secret against environment variables"""
        # For production, only allow the configured student email/secret
        return email == self.STUDENT_EMAIL and secret == self.STUDENT_SECRET

# Create settings instance
settings = Settings()

# Print configuration for verification (without exposing secrets)
print("✓ Settings loaded successfully")
print(f"✓ Using Gemini model: {settings.GEMINI_MODEL_PRIMARY}")
print(f"✓ Browser headless: {settings.BROWSER_HEADLESS}")
print(f"✓ Total timeout: {settings.TOTAL_TIMEOUT}s")
print(f"✓ Student email configured: {settings.STUDENT_EMAIL[:5]}...")  # Only show first 5 chars