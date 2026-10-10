import io
import requests
import soundfile as sf
import numpy as np
from typing import Optional
from groq import Groq
from config import GROQ_API_KEY, DEEPGRAM_API_KEY, STT_PROVIDER, SAMPLE_RATE

WHISPER_HALLUCINATIONS = {
    "gracias", "gracias.", "¡gracias!", "muchas gracias", "muchas gracias.", "¡muchas gracias!",
    "gracias por ver", "gracias por ver el video", "gracias por ver el vídeo.", "gracias por su atención",
    "subtítulos por la comunidad de amara.org", "suscríbete", "suscríbete al canal",
    "subtítulos por", "subtítulos realizados por", "amara.org", "you", "continuará", "continuará..."
}

def normalize_audio_for_whispers(audio_data: np.ndarray) -> np.ndarray:
    """
    Normaliza y amplifica audios con susurros o voz baja
    para que el modelo acústico entienda cada palabra con máxima claridad.
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data
    peak = float(np.max(np.abs(audio_data)))
    if 0.001 < peak < 0.40:
        # Amplificar suavemente hasta 0.70 de amplitud máxima (sin saturar)
        gain = min(0.70 / peak, 5.0)
        return (audio_data * gain).astype(np.float32)
    return audio_data

class SpeechToText:
    """Conversor de Voz a Texto de ultra baja latencia con Deepgram Nova-2 y Groq Whisper"""
    def __init__(self):
        self.provider = STT_PROVIDER.lower()
        self.deepgram_key = DEEPGRAM_API_KEY
        self.groq_key = GROQ_API_KEY
        
        # Cliente Groq
        self.groq_client = Groq(api_key=self.groq_key) if self.groq_key else None
        
        # Sesión HTTP persistente para Deepgram Nova-3 (usa keyterm para vocabulario guiado)
        self.http_session = requests.Session()
        self.deepgram_url = (
            "https://api.deepgram.com/v1/listen?"
            "model=nova-3&language=es-419&smart_format=true&punctuate=true&"
            "keyterm=Elena&keyterm=Lucía&keyterm=Paco&keyterm=círculos&"
            "keyterm=cuadernillo&keyterm=monedas&keyterm=tarjetas&keyterm=animales&keyterm=figuras"
        )

    def _transcribe_deepgram(self, wav_bytes: bytes) -> Optional[str]:
        if not self.deepgram_key:
            return None
        headers = {
            "Authorization": f"Token {self.deepgram_key}",
            "Content-Type": "audio/wav"
        }
        try:
            res = self.http_session.post(self.deepgram_url, headers=headers, data=wav_bytes, timeout=12)
            if res.status_code == 200:
                data = res.json()
                channels = data.get("results", {}).get("channels", [])
                if channels:
                    alts = channels[0].get("alternatives", [])
                    if alts:
                        return alts[0].get("transcript", "").strip()
            else:
                print(f"⚠️ Deepgram error ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"⚠️ Excepción en Deepgram: {e}")
        return None

    def _transcribe_groq(self, wav_bytes: bytes) -> str:
        if not self.groq_client:
            return ""
        try:
            transcription = self.groq_client.audio.transcriptions.create(
                file=("audio.wav", wav_bytes),
                model="whisper-large-v3-turbo",
                language="es",
                temperature=0.0,
                prompt="Elena, Lucía, Paco, matemáticas, figuras, cuadernillo, círculos, tarjetas, monedas, colores, animales, reto."
            )
            return transcription.text.strip()
        except Exception as e:
            print(f"⚠️ Error en Groq Whisper: {e}")
            return ""

    def transcribe(self, audio_data: np.ndarray) -> str:
        if audio_data is None or len(audio_data) == 0:
            return ""

        # 1. Normalizar ganancia para capturar susurros y murmullos infantiles
        boosted_audio = normalize_audio_for_whispers(audio_data)

        # 2. Convertir a WAV en memoria
        buffer = io.BytesIO()
        buffer.name = "audio.wav"
        sf.write(buffer, boosted_audio, SAMPLE_RATE, format="WAV")
        wav_bytes = buffer.getvalue()

        raw_text = ""

        # 3. Transcribir con Deepgram (o Groq según configuración)
        if self.provider == "deepgram" and self.deepgram_key:
            deepgram_result = self._transcribe_deepgram(wav_bytes)
            if deepgram_result is not None:
                raw_text = deepgram_result
            elif self.groq_client:
                # Fallback automático a Groq si Deepgram fallara
                raw_text = self._transcribe_groq(wav_bytes)
        else:
            raw_text = self._transcribe_groq(wav_bytes)

        # 4. Filtrar alucinaciones de silencio
        clean_check = raw_text.lower().strip(" ¡!¿?.,;:-_")
        if clean_check in WHISPER_HALLUCINATIONS or any(clean_check.startswith(h) for h in ["gracias por ver", "subtítulos", "subtitulos", "suscríbete"]):
            return ""

        return raw_text
