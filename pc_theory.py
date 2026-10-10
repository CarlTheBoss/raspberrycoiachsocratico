import os
import json
from typing import Dict, Any, Optional

PC_TEORY_PATH = os.path.join(os.path.dirname(__file__), "PC_Teory.py")

# Mapeo pedagógico adaptado para niños (1.er y 2.° grado de primaria)
KIDS_DIMENSION_ADAPTATIONS = {
    "DIM-01": {
        "name": "Interpretación",
        "focus_kids": "Comprender el problema y separar los datos clave",
        "observable_kids": "¿El niño comprende qué le piden, qué objetos o animales están en el juego y qué reglas aplican?",
        "ars_check": "Aceptabilidad: ¿identifica correctamente los datos visuales de la página?",
        "socratic_guide": "¿De qué trata este ejercicio o qué vemos primero sobre la mesa?"
    },
    "DIM-02": {
        "name": "Análisis",
        "focus_kids": "Descomponer en partes (subgrupos) y comparar parte vs. todo",
        "observable_kids": "¿El niño puede agrupar por color/tamaño y entender que el total siempre tiene más que una sola parte?",
        "ars_check": "Relevancia: ¿agrupa según el criterio solicitado (color, tamaño) sin confundirlos?",
        "socratic_guide": "Si separamos las figuras por colores, ¿qué forma cada montoncito?"
    },
    "DIM-03": {
        "name": "Evaluación",
        "focus_kids": "Evaluar si una afirmación es verdadera o falsa",
        "observable_kids": "¿El niño juzga si lo que dijo Paco o Lucía tiene sentido lógico basándose en lo que ve en la página?",
        "ars_check": "Aceptabilidad y Lógica: ¿detecta si una afirmación es falsa (ej. 'todos los círculos son grandes')?",
        "socratic_guide": "¿Estás de acuerdo con lo que dijo Paco/Lucía? ¿Por qué sí o por qué no?"
    },
    "DIM-04": {
        "name": "Inferencia",
        "focus_kids": "Deducir consecuencias de las reglas y predecir resultados",
        "observable_kids": "¿El niño puede deducir qué pasa al lanzar la moneda (cara/sello) o cuántas tarjetas quedan disponibles?",
        "ars_check": "Suficiencia: ¿deduce si alcanzan las tarjetas para tomar dos del mismo animal?",
        "socratic_guide": "Si la regla dice dos iguales y solo queda uno, ¿qué se deduce que puede o no puede hacer?"
    },
    "DIM-05": {
        "name": "Explicación",
        "focus_kids": "Expresar el porqué con sus propias palabras",
        "observable_kids": "¿El niño puede dar una razón clara de por qué eligió esa respuesta en lugar de solo adivinar?",
        "ars_check": "Claridad argumental: ¿puede decir 'porque 8 es más que 7' o 'porque eran del mismo color'?",
        "socratic_guide": "¿Cómo le explicarías a un amiguito la razón por la que elegiste esa respuesta?"
    },
    "DIM-06": {
        "name": "Autorregulación",
        "focus_kids": "Revisar su propio trabajo, aprender del error y metacognición",
        "observable_kids": "¿El niño revisa si contó bien, reconoce si se equivocó y reflexiona sobre cómo aprendió?",
        "ars_check": "Autocorrección: ¿vuelve a contar si nota una contradicción?",
        "socratic_guide": "¿Qué hiciste para no equivocarte? ¿Te pareció fácil o qué parte te costó más?"
    },
    "DIM-07": {
        "name": "Fundamentos Lógicos (Marco ARS)",
        "focus_kids": "Aplicar cuantificadores ('Todos', 'Algunos', 'Ninguno') y reglas lógicas",
        "observable_kids": "¿El niño distingue entre 'todos' los círculos y 'algunos' círculos?",
        "ars_check": "Marco ARS completo: Datos verdaderos (A), respuesta pertinente (R) y conteo completo (S).",
        "socratic_guide": "¿Acaso TODOS los círculos son grandes, o solo ALGUNOS de ellos?"
    }
}

class CriticalThinkingManager:
    """Administrador del marco teórico de Pensamiento Crítico (APA Delphi + Marco ARS)"""
    def __init__(self, file_path: str = PC_TEORY_PATH):
        self.file_path = file_path
        self.raw_data = self._load_data()
        self.dimensions_by_id = {d["dimension_id"]: d for d in self.raw_data.get("critical_thinking_dimensions", [])}

    def _load_data(self) -> Dict[str, Any]:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando PC_Teory.py: {e}")
        return {}

    def get_dimension_info(self, dim_id: str) -> Optional[Dict[str, Any]]:
        raw = self.dimensions_by_id.get(dim_id)
        adaptation = KIDS_DIMENSION_ADAPTATIONS.get(dim_id, {})
        if not raw and not adaptation:
            return None
        return {
            "id": dim_id,
            "name": adaptation.get("name", raw.get("dimension_name") if raw else ""),
            "formal_symbol": raw.get("formal_symbol") if raw else "",
            "focus_kids": adaptation.get("focus_kids", ""),
            "observable_kids": adaptation.get("observable_kids", ""),
            "ars_check": adaptation.get("ars_check", ""),
            "socratic_guide": adaptation.get("socratic_guide", ""),
            "formal_definition": raw.get("theoretical_definition") if raw else "",
            "raw_hints": raw.get("socratic_prompting_hints", []) if raw else []
        }

    def get_prompt_evaluation_scaffolding(self, dim_id: Optional[str] = None) -> str:
        """Genera el bloque pedagógico de evaluación de Pensamiento Crítico para el LLM"""
        lines = [
            "🧠 [MARCO DE EVALUACIÓN SOCRÁTICA - PENSAMIENTO CRÍTICO (APA Delphi / Facione & Marco ARS)]:"
        ]
        
        if dim_id and dim_id in KIDS_DIMENSION_ADAPTATIONS:
            info = self.get_dimension_info(dim_id)
            lines.append(f"- Dimensión activa en este ejercicio: {info['name']} ({info['id']})")
            lines.append(f"- Foco cognitivo: {info['focus_kids']}")
            lines.append(f"- Qué debes observar en el niño: {info['observable_kids']}")
            lines.append(f"- Evaluación ARS: {info['ars_check']}")
            lines.append(f"- Pregunta guía recomendada: \"{info['socratic_guide']}\"")
        else:
            lines.append("- Evalúa al niño usando el Marco ARS adaptado a primaria:")
            lines.append("  * A (Aceptabilidad): ¿Los datos o números que dice el niño son verdaderos según la ilustración?")
            lines.append("  * R (Relevancia): ¿Lo que responde apunta exactamente a lo que se le preguntó?")
            lines.append("  * S (Suficiencia): ¿Tuvo en cuenta todos los elementos necesarios o concluyó apresuradamente?")
            lines.append("- Guía al niño paso a paso a través de las 6 etapas Delphi: Interpretación -> Análisis -> Evaluación -> Inferencia -> Explicación -> Autorregulación.")

        return "\n".join(lines)

# Instancia global
pc_theory = CriticalThinkingManager()
