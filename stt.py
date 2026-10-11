import io
import requests
import soundfile as sf
import numpy as np
from typing import Optional
from groq import Groq
from google import genai
from google.genai import types
from config import GROQ_API_KEY, DEEPGRAM_API_KEY, GEMINI_API_KEY, GEMINI_TRANSCRIBE_MODEL, STT_PROVIDER, SAMPLE_RATE

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
        gain = min(0.70 / peak, 5.0)
        return (audio_data * gain).astype(np.float32)
    return audio_data

class SpeechToText:
    """Conversor de Voz a Texto con Gemini Transcribe, Deepgram Nova-3 y Groq Whisper"""
    def __init__(self):
        self.provider = STT_PROVIDER.lower()
        self.deepgram_key = DEEPGRAM_API_KEY
        self.groq_key = GROQ_API_KEY
        self.gemini_key = GEMINI_API_KEY
        self.gemini_model = GEMINI_TRANSCRIBE_MODEL

        # Cliente Google Gemini
        self.gemini_client = genai.Client(api_key=self.gemini_key) if self.gemini_key else None
        
        # Cliente Groq
        self.groq_client = Groq(api_key=self.groq_key) if self.groq_key else None
        
        # Sesión HTTP persistente para Deepgram Nova-3
        self.http_session = requests.Session()
        self.deepgram_url = (
            "https://api.deepgram.com/v1/listen?"
            "model=nova-3&language=es-419&smart_format=true&punctuate=true&"
            "keyterm=Elena&keyterm=Lucía&keyterm=Paco&keyterm=círculos&"
            "keyterm=cuadernillo&keyterm=monedas&keyterm=tarjetas&keyterm=animales&keyterm=figuras"
        )

    def _transcribe_gemini(self, wav_bytes: bytes) -> Optional[str]:
        if not self.gemini_client:
            return None
        try:
            # Instrucción concisa para transcripción precisa enfocada en el contexto escolar
            prompt = (
                "Transcribe de forma literal y exacta lo que dice el niño en este audio en español. "
                "Devuelve ÚNICAMENTE el texto transcrito sin comentarios ni explicaciones adicionales. "
                "Contexto de vocabulario clave: Elena, Lucía, Paco, figuras, círculos, colores, reto, cuadernillo."
            )
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=wav_bytes,
                        mime_type="audio/wav"
                    )
                ]
            )
            # Extraer texto de parts (incluyendo audio_transcription) limpiamente y sin errores NoneType
            if response and response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    text_parts = []
                    for part in candidate.content.parts:
                        if getattr(part, "text", None):
                            text_parts.append(part.text)
                        elif hasattr(part, "audio_transcription") and getattr(part.audio_transcription, "text", None):
                            text_parts.append(part.audio_transcription.text)
                    if text_parts:
                        return " ".join(text_parts).strip()
            if response and getattr(response, "text", None):
                return response.text.strip()
        except Exception as e:
            print(f"⚠️ Excepción en Gemini Transcribe ({self.gemini_model}): {e}")
            # Fallback a Deepgram / Groq si Gemini devolviera respuesta vacía
            pass
            # Fallback a gemini-2.5-flash si el modelo especializado tuviera alguna restricción
            if "not found" in str(e).lower() or "404" in str(e):
                try:
                    response = self.gemini_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[
                            "Transcribe exactamente el audio en español:",
                            types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav")
                        ]
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception:
                    pass
        return None

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

        # 3. Transcribir según proveedor (gemini, deepgram o groq)
        if self.provider == "gemini" and self.gemini_client:
            gemini_result = self._transcribe_gemini(wav_bytes)
            if gemini_result is not None:
                raw_text = gemini_result
            elif self.deepgram_key:
                raw_text = self._transcribe_deepgram(wav_bytes) or ""
            elif self.groq_client:
                raw_text = self._transcribe_groq(wav_bytes)
        elif self.provider == "deepgram" and self.deepgram_key:
            deepgram_result = self._transcribe_deepgram(wav_bytes)
            if deepgram_result is not None:
                raw_text = deepgram_result
            elif self.groq_client:
                raw_text = self._transcribe_groq(wav_bytes)
        else:
            raw_text = self._transcribe_groq(wav_bytes)

        # 4. Filtrar alucinaciones de silencio
        clean_check = raw_text.lower().strip(" ¡!¿?.,;:-_")
        if clean_check in WHISPER_HALLUCINATIONS or any(clean_check.startswith(h) for h in ["gracias por ver", "subtítulos", "subtitulos", "suscríbete"]):
            return ""

        return raw_text
