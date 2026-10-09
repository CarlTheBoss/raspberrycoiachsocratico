import os
import json
import threading
from typing import Dict, Any
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "episodic_memory.json")

DEFAULT_MEMORY = {
    "child_name": "",
    "interests": [],
    "topics_worked": [],
    "strengths": [],
    "areas_to_reinforce": [],
    "last_session_summary": "",
    "recent_milestones": []
}

class EpisodicMemory:
    """
    Sistema de Memoria Episódica persistente que aprende y recuerda
    el progreso, gustos y dificultades del niño en segundo plano.
    """
    def __init__(self):
        self.memory = self._load_memory()
        self.client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

    def _load_memory(self) -> Dict[str, Any]:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando memoria: {e}")
        return DEFAULT_MEMORY.copy()

    def _save_memory(self):
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Error guardando memoria: {e}")

    def get_memory_context(self) -> str:
        """Genera el contexto episódico para inyectar al prompt de Tobi"""
        mem = self.memory
        if not any([mem.get("topics_worked"), mem.get("interests"), mem.get("last_session_summary")]):
            return ""

        context_lines = ["\n📌 [MEMORIA EPISÓDICA DEL NIÑO]:"]
        if mem.get("child_name"):
            context_lines.append(f"- Nombre del niño: {mem['child_name']}")
        if mem.get("interests"):
            context_lines.append(f"- Intereses/Gustos: {', '.join(mem['interests'])}")
        if mem.get("topics_worked"):
            context_lines.append(f"- Temas que ha practicado: {', '.join(mem['topics_worked'])}")
        if mem.get("strengths"):
            context_lines.append(f"- Fortalezas: {', '.join(mem['strengths'])}")
        if mem.get("areas_to_reinforce"):
            context_lines.append(f"- Áreas por reforzar: {', '.join(mem['areas_to_reinforce'])}")
        if mem.get("last_session_summary"):
            context_lines.append(f"- Resumen de sesiones previas: {mem['last_session_summary']}")
        context_lines.append("Recuerda estos datos para personalizar tu trato y conectar con el niño con naturalidad.\n")

        return "\n".join(context_lines)

    def update_in_background(self, user_text: str, robot_reply: str):
        """Lanza la extracción de memoria episódica en un hilo secundario sin bloquear la voz"""
        t = threading.Thread(target=self._extract_insights, args=(user_text, robot_reply), daemon=True)
        t.start()

    def _extract_insights(self, user_text: str, robot_reply: str):
        if not self.client:
            return

        extraction_prompt = f"""
Analiza este breve intercambio entre un niño y su robot tutor Tobi:
Niño: "{user_text}"
Tobi: "{robot_reply}"

Memoria actual:
{json.dumps(self.memory, ensure_ascii=False)}

Extrae en formato JSON únicamente los datos nuevos descubiertos (si no hay datos nuevos, mantén los existentes):
{{
  "child_name": "nombre si lo mencionó, o mantener actual",
  "interests": ["lista de gustos o ejemplos que le gustan (e.g. fútbol, dinosaurios)"],
  "topics_worked": ["materias o temas practicados (e.g. tabla del 9, suma de fracciones)"],
  "strengths": ["lo que el niño entendió o logró"],
  "areas_to_reinforce": ["donde tuvo dudas o errores"],
  "last_session_summary": "1 oración que resuma lo practicado recientemente"
}}
Responde SOLO con el JSON válido.
"""
        try:
            res = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=extraction_prompt,
                config={"response_mime_type": "application/json"}
            )
            if res.text:
                new_data = json.loads(res.text.strip())
                self.memory.update(new_data)
                self._save_memory()
        except Exception:
            pass
