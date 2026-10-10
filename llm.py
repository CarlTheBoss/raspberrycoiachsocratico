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
        
        # Inyectar memoria episódica en las instrucciones del sistema
        system_instructions = SOCRATIC_KIDS_PROMPT + "\n" + self.memory.get_memory_context()
        
        self.chat = self.client.chats.create(
            model=GEMINI_MODEL,
            config={
                "system_instruction": system_instructions,
                "temperature": 0.7,
            }
        )

    def get_current_page(self) -> int:
        return self.curriculum.get_session()["current_page"]

    def set_page(self, page_number: int):
        self.curriculum.set_current_page(page_number)

    def stream_sentences(self, user_text: str) -> Generator[str, None, None]:
        """
        Envía el mensaje a Gemini y genera oraciones completas y válidas para TTS.
        """
        if not user_text or not user_text.strip():
            return

        # Consultar la base de datos SQLite para saber la página exacta, contexto y pistas
        curriculum_context = self.curriculum.get_agent_context(user_text)
        augmented_prompt = f"{curriculum_context}\n[MENSAJE DEL NIÑO]: {user_text}"

        buffer = ""
        full_response = []
        # Puntuadores que delimitan el fin de una oración
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
                        sentence = buffer[:end_pos].strip()
                        buffer = buffer[end_pos:].strip()

                        # Filtrar cadenas vacías o solo puntuación
                        clean_sentence = re.sub(r'^[¿¡\s.!?]+$', '', sentence).strip()
                        if len(clean_sentence) >= 3:
                            yield sentence

                        match = sentence_end_pattern.search(buffer)

            # Enviar lo que haya quedado en el buffer
            remaining = buffer.strip()
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
