import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./harvex.db")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# AI Provider
AI_PROVIDER = os.getenv("AI_PROVIDER", "nvidia")

# NVIDIA NIM — Main AI
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_TEXT_MODEL = os.getenv("NVIDIA_TEXT_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
NVIDIA_REASONING_FALLBACK_MODEL = os.getenv("NVIDIA_REASONING_FALLBACK_MODEL", "")

# NVIDIA NIM — Vision
NVIDIA_VISION_API_KEY = os.getenv("NVIDIA_VISION_API_KEY", "")
NVIDIA_VISION_MODEL = os.getenv("NVIDIA_VISION_MODEL", "meta/llama-3.2-90b-vision-instruct")

# NVIDIA NIM — Translation
NVIDIA_TRANSLATION_API_KEY = os.getenv("NVIDIA_TRANSLATION_API_KEY", "")
NVIDIA_TRANSLATION_MODEL = os.getenv("NVIDIA_TRANSLATION_MODEL", "nvidia/riva-translate-4b-instruct-v2")

# Ollama (fallback)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2:0.5b")

# AI Timeouts
AI_REQUEST_TIMEOUT = int(os.getenv("AI_REQUEST_TIMEOUT", "60"))
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "2"))

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./storage/uploads")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
