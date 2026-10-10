import re
from typing import Generator
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL
from prompt import SOCRATIC_KIDS_PROMPT
from memory import EpisodicMemory
from curriculum_db import curriculum

class SocraticCoach:
    """Manejador de conversación con Gemini con Streaming de Oraciones y Memoria Episódica"""
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("❌ GEMINI_API_KEY no está configurada en el archivo .env")
        
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.memory = EpisodicMemory()
        self.curriculum = curriculum
        self.curriculum.reset_session()
        
        # Inyectar el marco socrático, el temario completo oficial y la memoria episódica
        system_instructions = (
            SOCRATIC_KIDS_PROMPT + "\n\n" +
            self.curriculum.get_full_curriculum_prompt() + "\n\n" +
            self.memory.get_memory_context()
        )
        
        self.chat = self.client.chats.create(
            model=GEMINI_MODEL,
            config={
                "system_instruction": system_instructions,
                "temperature": 0.7,
            }
        )

    def stream_sentences(self, user_text: str) -> Generator[str, None, None]:
        """
        Envía el mensaje a Gemini y genera oraciones balanceadas para TTS sin microcortes ni demoras.
        """
        if not user_text or not user_text.strip():
            return

        augmented_prompt = f"[MENSAJE DEL NIÑO]: {user_text}"

        buffer = ""
        full_response = []
        pending_chunk = ""
        sentence_end_pattern = re.compile(r'([.!?\n]+)')

        try:
            response_stream = self.chat.send_message_stream(augmented_prompt)
            
            for chunk in response_stream:
                if chunk.text:
                    buffer += chunk.text
                    full_response.append(chunk.text)
                    print(chunk.text, end="", flush=True)

                    # Buscar si hay un delimitador de fin de oración
                    match = sentence_end_pattern.search(buffer)
                    while match:
                        end_pos = match.end()
                        raw_sentence = buffer[:end_pos].strip()
                        buffer = buffer[end_pos:].strip()

                        clean_sentence = re.sub(r'^[¿¡\s.!?]+$', '', raw_sentence).strip()
                        if clean_sentence:
                            if pending_chunk:
                                candidate = f"{pending_chunk} {raw_sentence}"
                            else:
                                candidate = raw_sentence

                            # Si el fragmento es muy breve (ej. "¡Hola!", "¡Así es!"), acumular con la siguiente frase
                            # para evitar que el reproductor termine antes de sintetizar la siguiente frase
                            if len(candidate) < 28 and not ("\n" in raw_sentence):
                                pending_chunk = candidate
                            else:
                                yield candidate
                                pending_chunk = ""

                        match = sentence_end_pattern.search(buffer)

            # Enviar lo que haya quedado acumulado
            remaining = f"{pending_chunk} {buffer}".strip()
            clean_remaining = re.sub(r'^[¿¡\s.!?]+$', '', remaining).strip()
            if len(clean_remaining) >= 2:
                yield remaining

            # Actualizar memoria episódica en segundo plano
            complete_text = "".join(full_response).strip()
            if complete_text:
                self.memory.update_in_background(user_text, complete_text)

        except Exception as e:
            print(f"\n⚠️ Error en Gemini: {e}")
            yield "¡Oh, me distraje un momento! ¿Podrías repetirme eso?"
