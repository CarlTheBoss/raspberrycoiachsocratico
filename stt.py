import io
import soundfile as sf
import numpy as np
from groq import Groq
from config import GROQ_API_KEY, SAMPLE_RATE

class SpeechToText:
    """Conversor de Voz a Texto ultra rápido y gratuito con Groq Whisper"""
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("❌ GROQ_API_KEY no está configurada en el archivo .env")
        self.client = Groq(api_key=GROQ_API_KEY)

    def transcribe(self, audio_data: np.ndarray) -> str:
        if audio_data is None or len(audio_data) == 0:
            return ""

        # Crear buffer WAV en memoria
        buffer = io.BytesIO()
        buffer.name = "audio.wav"
        sf.write(buffer, audio_data, SAMPLE_RATE, format="WAV")
        buffer.seek(0)

        try:
            transcription = self.client.audio.transcriptions.create(
                file=("audio.wav", buffer.read()),
                model="whisper-large-v3-turbo",
                language="es",
                temperature=0.0
            )
            return transcription.text.strip()
        except Exception as e:
            print(f"⚠️ Error al transcribir con Groq Whisper: {e}")
            return ""
