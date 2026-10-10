import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
STT_PROVIDER = os.getenv("STT_PROVIDER", "deepgram")

# Modelo de LLM
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Fish Audio TTS Config
FISH_TTS_MODEL = os.getenv("FISH_TTS_MODEL", "s2.1-pro-free")
FISH_REFERENCE_ID = os.getenv("FISH_REFERENCE_ID", "")

# Audio Recording Config
SAMPLE_RATE = 16000  # 16kHz
CHANNELS = 1         # Mono
SILENCE_DURATION = float(os.getenv("SILENCE_DURATION", "2.8"))
ENERGY_THRESHOLD = float(os.getenv("ENERGY_THRESHOLD", "0.0035"))
INTERRUPT_THRESHOLD = float(os.getenv("INTERRUPT_THRESHOLD", "0.025"))

# GPIO Pin para botón (opcional en Raspberry Pi)
GPIO_BUTTON_PIN = os.getenv("GPIO_BUTTON_PIN", "")
