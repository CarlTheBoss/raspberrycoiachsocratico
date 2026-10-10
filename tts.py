import io
import os
import tempfile
import requests
import soundfile as sf
import sounddevice as sd
import numpy as np
from typing import Tuple, Optional
from config import FISH_AUDIO_API_KEY, FISH_TTS_MODEL, FISH_REFERENCE_ID

class TextToSpeech:
    """Sintetizador de voz hiper-realista usando Fish Audio S2.1 Pro optimizado para baja latencia"""
    def __init__(self):
        if not FISH_AUDIO_API_KEY:
            raise ValueError("❌ FISH_AUDIO_API_KEY no está configurada en el archivo .env")
        self.api_key = FISH_AUDIO_API_KEY
        self.model = FISH_TTS_MODEL
        self.reference_id = FISH_REFERENCE_ID
        self.endpoint = "https://api.fish.audio/v1/tts"
        
        # Sesión HTTP persistente con Keep-Alive para eliminar latencia de TLS en cada frase
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "model": self.model
        }

    def generate_audio(self, text: str) -> Optional[Tuple[np.ndarray, int]]:
        """Genera el audio con Fish Audio y retorna (audio_data, sample_rate) en streaming optimizado"""
        if not text or not text.strip():
            return None

        payload = {
            "text": text.strip(),
            "format": "mp3",
            "latency": "balanced"
        }

        if self.reference_id:
            payload["reference_id"] = self.reference_id

        try:
            response = self.session.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"⚠️ Error de Fish Audio TTS ({response.status_code}): {response.text}")
                return None

            # Leer MP3 directamente en memoria con soundfile
            audio_buffer = io.BytesIO(response.content)
            data, fs = sf.read(audio_buffer, dtype="float32")
            return data, fs

        except Exception as e:
            print(f"⚠️ Excepción en Fish Audio TTS: {e}")
            return None

    def speak(self, text: str):
        """Reproduce directamente sin interrupción (ej. saludo inicial)"""
        result = self.generate_audio(text)
        if result:
            data, fs = result
            sd.play(data, fs)
            sd.wait()
