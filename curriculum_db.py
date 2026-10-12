import os
import sqlite3
import json
import re
from typing import Optional, List, Dict, Any
from pc_theory import pc_theory

DB_PATH = os.path.join(os.path.dirname(__file__), "curriculum.db")

CURRICULUM_DATA = [
    {
        "page_number": 1,
        "challenge_title": "Carátula: Resolvemos problemas jugando 2",
        "topic": "Presentación y competencia matemática",
        "visual_context": "Carátula oficial de Educación Primaria (1.er y 2.° grado) de MINEDU Perú. Muestra a Lucía, Paco y un profesor alrededor de una mesa con bloques lógicos (círculos de colores y tamaños, triángulos, cuadrados, rectángulos). Competencia: 'Resuelve problemas de cantidad'.",
        "pedagogical_goal": "Introducir a los personajes Lucía y Paco en un entorno lúdico para resolver problemas de cantidad.",
        "exercises": []
    },
    {
        "page_number": 2,
        "challenge_title": "Orientaciones iniciales",
        "topic": "Pautas pedagógicas y metodológicas",
        "visual_context": "Indicaciones para niños y acompañantes adultos. Iconos de trabajo: 'Trabaja individualmente', 'Trabaja acompañada o acompañado', 'Jueguen'. Se explica que aprenderán a agrupar objetos, formar grupos y subgrupos, y reconocer que dentro de un todo hay cantidades menores.",
        "pedagogical_goal": "Sensibilizar al estudiante y a la familia sobre la importancia del juego y la exploración matemática.",
        "exercises": []
    },
    {
        "page_number": 3,
        "challenge_title": "¿Qué encontrarás en este fascículo?",
        "topic": "Hoja de ruta del fascículo",
        "visual_context": "Presentación visual de los 2 retos: Reto 1: 'Organizamos nuestros objetos' (Lucía guardando figuras circulares en bolsas) y Reto 2: 'Rotulamos las cajas' (Lucía y Paco con cajas rotuladas).",
        "pedagogical_goal": "Estructurar la experiencia de aprendizaje en dos etapas.",
        "exercises": []
    },
    {
        "page_number": 4,
        "challenge_title": "Reto 1: Organizamos nuestros objetos",
        "topic": "Atributos geométricos: Forma vs. Color",
        "visual_context": "Lucía y Paco tienen cajas de colección. Lucía dice que guardó bloques lógicos de la misma forma. Paco conjetura: 'Me parece que pueden ser figuras de color amarillo'. Al abrir la caja se ven 7 figuras y TODAS son círculos: 4 rojos (2 grande, 2 pequeños), 2 amarillos (1 grande, 1 pequeño) y 1 azul (pequeño). No hay triángulos ni cuadrados.",
        "pedagogical_goal": "Distinguir claramente el atributo de 'forma' frente al atributo de 'color'.",
        "exercises": [
            {
                "exercise_order": 1,
                "dimension_id": "DIM-01",
                "question_text": "Lucía dice que en una caja colocó algunos bloques lógicos que tienen una misma forma. ¿Cómo serán las figuras de Lucía?",
                "expected_concept": "Todas las figuras deben compartir la misma forma geométrica (por ejemplo, todas redondas/círculos o todas triángulos), sin importar su color ni su tamaño.",
                "socratic_hints": [
                    "¿Qué condición mencionó Lucía sobre sus figuras?",
                    "¿Ella habló del color o solo se fijó en la forma?",
                    "Si todas tienen que compartir la misma forma, ¿cómo tendrían que ser?"
                ],
                "keywords": "forma, figuras, bloques lógicos, Lucía, caja, círculos",
                "solution_detail": "Tienen la misma forma geométrica; por ejemplo, todas son círculos."
            },
            {
                "exercise_order": 2,
                "dimension_id": "DIM-03",
                "question_text": "Paco respondió: 'Me parece que pueden ser figuras de color amarillo'. ¿Estás de acuerdo con lo que dice Paco?, ¿por qué?",
                "expected_concept": "No necesariamente, porque Lucía dijo que tenían la misma forma, no el mismo color. Pueden ser de varios colores siempre que compartan la misma forma.",
                "socratic_hints": [
                    "Recuerda lo que dijo Lucía: ¿dijo que eran amarillas o habló de su forma?",
                    "Si agrupas objetos por su forma, ¿es obligatorio que todos tengan el mismo color?",
                    "¿Podría haber círculos de colores diferentes en su caja?"
                ],
                "keywords": "Paco, amarillo, de acuerdo, por qué, conjetura, no estoy de acuerdo",
                "solution_detail": "No se está de acuerdo porque la condición de Lucía fue la forma, no el color."
            }
        ]
    },
    {
        "page_number": 5,
        "challenge_title": "Reto 1: Organizamos nuestros objetos",
        "topic": "Observación, atributos y agrupación por color",
        "visual_context": "Las 7 figuras de Lucía se observan en un recuadro amarillo: 4 círculos rojos (2 grande, 2 pequeños), 2 círculos amarillos (1 grande, 1 pequeño) y 1 círculo azul pequeño. Paco propone: 'Yo propongo que las agrupe por colores. ¿Cómo lo haría?'. Hay un recuadro para dibujar las agrupaciones.",
        "pedagogical_goal": "Clasificar colecciones de objetos por color e identificar variaciones de tamaño.",
        "exercises": [
            {
                "exercise_order": 1,
                "dimension_id": "DIM-01",
                "question_text": "¿Qué figuras había en la caja de Lucía?",
                "expected_concept": "Había círculos (figuras circulares o redondas).",
                "socratic_hints": [
                    "Mira la forma de las figuras que sacó Lucía: ¿tienen esquinas o son redonditas?",
                    "¿Cómo se llama esa figura geométrica que no tiene puntas ni lados rectos?"
                ],
                "keywords": "figuras, caja de Lucía, qué figuras, círculos, redondas",
                "solution_detail": "Todas son círculos."
            },
            {
                "exercise_order": 2,
                "dimension_id": "DIM-02",
                "question_text": "¿Todas son iguales de tamaño y colores?, ¿por qué?",
                "expected_concept": "No, porque tienen tamaños diferentes (grandes y pequeños) y tres colores distintos (rojo, amarillo y azul).",
                "socratic_hints": [
                    "Fíjate en los tamaños: ¿son todas del mismo porte o hay unas más grandes que otras?",
                    "¿Y qué colores distintos puedes ver en la mesa?"
                ],
                "keywords": "tamaño, colores, iguales, diferentes, por qué, rojo, amarillo, azul",
                "solution_detail": "No son iguales: varían en tamaño (grande, pequeño) y en color (rojo, amarillo, azul)."
            },
            {
                "exercise_order": 3,
                "dimension_id": "DIM-02",
                "question_text": "Paco propone agrupar las figuras por colores. ¿Cómo lo haría? Dibuja o explica las agrupaciones.",
                "expected_concept": "Se forman 3 grupos: un grupo con los 4 círculos rojos, otro con los 2 amarillos y otro con el único círculo azul.",
                "socratic_hints": [
                    "¿Cuántos colores diferentes ves en la mesa?",
                    "Si juntas los que tienen el mismo color, ¿cuántos grupos formarías y cuántas figuras tendría cada uno?"
                ],
                "keywords": "agrupar, colores, cómo lo haría, grupos, bolsas, tres grupos",
                "solution_detail": "Separar en 3 grupos: rojos (4), amarillos (2) y azul (1)."
            }
        ]
    },
    {
        "page_number": 6,
        "challenge_title": "Reto 1: Organizamos nuestros objetos",
        "topic": "Inclusión de clases: El Todo frente a las Partes",
        "visual_context": "Lucía junto a los 7 círculos y 2 bolsas vacías. Círculos: 4 rojos (2 grande, 2 pequeños), 2 amarillos (1 grande, 1 pequeño) y 1 azul pequeño. En total hay 7 círculos. Preguntas sobre agrupar en 2 bolsas y comparar el total de círculos frente a subconjuntos.",
        "pedagogical_goal": "Comprender la inclusión de clases de Piaget: el conjunto total de elementos siempre es cuantitativamente mayor que cualquier subconjunto propio.",
        "exercises": [
            {
                "exercise_order": 1,
                "dimension_id": "DIM-01",
                "question_text": "¿Cuántos grupos se han formado y cómo son los grupos que se han formado?",
                "expected_concept": "Se formaron 3 grupos por color: un grupo de círculos rojos (4), un grupo de círculos amarillos (2) y un grupo de círculos azules (1).",
                "socratic_hints": [
                    "Al separar por colores, ¿cuántos grupitos obtuviste?",
                    "¿De qué color es cada uno de esos grupitos?"
                ],
                "keywords": "cuántos grupos, cómo son, grupos formados, 3 grupos",
                "solution_detail": "3 grupos: grupo rojo, grupo amarillo y grupo azul."
            },
            {
                "exercise_order": 2,
                "dimension_id": "DIM-02",
                "question_text": "En el grupo de figuras que tiene Lucía, ¿hay más círculos rojos o amarillos?",
                "expected_concept": "Hay más círculos rojos (hay 4 círculos rojos y solo 2 amarillos; 4 > 2).",
                "socratic_hints": [
                    "¿Cuántos círculos rojos contaste en la mesa?",
                    "¿Y cuántos círculos amarillos hay?",
                    "¿Cuál número es mayor: el 4 o el 2?"
                ],
                "keywords": "más círculos rojos o amarillos, comparar colores, rojo, amarillo, 4 rojos",
                "solution_detail": "Hay más círculos rojos (4 rojos vs. 2 amarillos)."
            },
            {
                "exercise_order": 3,
                "dimension_id": "DIM-02",
                "question_text": "Lucía ha decidido organizar sus figuras de círculos en dos bolsas. ¿Qué agrupaciones podría hacer con las figuras que seleccionó?",
                "expected_concept": "Puede agrupar por tamaño (en una bolsa círculos grandes y en la otra círculos pequeños) o por combinación de colores (rojos en una bolsa y amarillos con azul en la otra).",
                "socratic_hints": [
                    "Si solo tienes dos bolsas, ¿qué característica podrías usar para dividirlas?",
                    "¿Podrías separar por tamaños o juntar dos colores en una bolsa?"
                ],
                "keywords": "dos bolsas, organizar, agrupaciones, tamaño, grandes, pequeños",
                "solution_detail": "Agrupar por tamaño (grandes en una bolsa y pequeños en otra) o por combinación de colores."
            },
            {
                "exercise_order": 4,
                "dimension_id": "DIM-02",
                "question_text": "¿Cuántos círculos tiene Lucía en total? ¿Ella tiene más círculos grandes o más círculos en total?",
                "expected_concept": "Tiene 7 círculos en total. Tiene más círculos en total (7) que círculos grandes (2), porque el total reúne a todos.",
                "socratic_hints": [
                    "Cuenta todos los círculos que tiene Lucía: ¿cuántos son en total?",
                    "¿Cuántos de ellos son del tamaño grande?",
                    "¿Qué número es mayor: el 7 del total o el 2 de los grandes?"
                ],
                "keywords": "círculos en total, más círculos grandes o en total, total, 7 círculos",
                "solution_detail": "Tiene 7 en total. Tiene más círculos en total (7 > 2 grandes)."
            },
            {
                "exercise_order": 5,
                "dimension_id": "DIM-02",
                "question_text": "¿Lucía tiene más círculos en total o más círculos pequeños?",
                "expected_concept": "Tiene más círculos en total (7 en total vs. 4 círculos pequeños o 5 no grandes).",
                "socratic_hints": [
                    "¿Cuántos círculos hay si cuentas todos juntos?",
                    "¿El grupo que tiene todas las piezas reunidas siempre es más grande que solo una parte?"
                ],
                "keywords": "más círculos en total o pequeños, total vs pequeños, más en total",
                "solution_detail": "Tiene más círculos en total (7 en total > círculos pequeños)."
            },
            {
                "exercise_order": 6,
                "dimension_id": "DIM-02",
                "question_text": "¿Tiene más círculos en total o más círculos rojos?",
                "expected_concept": "Tiene más círculos en total (7 en total vs. 4 rojos).",
                "socratic_hints": [
                    "¿Cuántos círculos rojos hay? (Son 4).",
                    "¿Y cuántos círculos hay en total en la mesa?",
                    "¿Qué cantidad es más grande: 7 o 4?"
                ],
                "keywords": "más círculos en total o rojos, total vs rojos, más en total",
                "solution_detail": "Tiene más círculos en total (7 en total > 4 rojos)."
            }
        ]
    },
    {
        "page_number": 7,
        "challenge_title": "Reto 1: Organizamos nuestros objetos",
        "topic": "Razonamiento deductivo ('Todos' vs 'Algunos') y metacognición",
        "visual_context": "Paco dice: '¡Todas las figuras de tamaño grande son círculos!'. Lucía dice: '¡Todos los círculos son grandes!'. Se ven las 7 figuras (todas son círculos: 3 grandes, 4 pequeños). Abajo ícono de foco 'Pensamos en lo que aprendimos'.",
        "pedagogical_goal": "Evaluar la validez de enunciados universales ('todos') y reflexionar sobre el aprendizaje.",
        "exercises": [
            {
                "exercise_order": 1,
                "dimension_id": "DIM-07",
                "question_text": "Paco dice: '¡Todas las figuras de tamaño grande son círculos!'. Lucía dice: '¡Todos los círculos son grandes!'. ¿Estás de acuerdo con lo que dicen Paco y Lucía? Explica.",
                "expected_concept": "Paco tiene razón porque las 3 figuras grandes son círculos. Lucía no tiene razón porque no todos los círculos son grandes: también hay pequeños.",
                "socratic_hints": [
                    "Mira solo las 3 figuras grandes: ¿qué forma tienen? ¿Paco dice la verdad?",
                    "Ahora revisa lo que dice Lucía: ¿todos los círculos de la mesa son grandotes, o también ves círculos chicos?",
                    "¿Quién tiene la razón de los dos?"
                ],
                "keywords": "de acuerdo con Paco y Lucía, figuras grandes círculos, todos los círculos son grandes, Paco tiene razón",
                "solution_detail": "Paco tiene razón porque las figuras grandes son círculos. Lucía no, porque hay círculos pequeños"
            },
            {
                "exercise_order": 2,
                "dimension_id": "DIM-06",
                "question_text": "Pensamos en lo que aprendimos: ¿Cómo lograste agrupar las figuras que tenía Lucía? ¿Qué hiciste para saber si hay más círculos en total o más círculos rojos?",
                "expected_concept": "Reflexión del estudiante explicando cómo comparó las cantidades (contar por separado y luego comparar el total con la parte).",
                "socratic_hints": [
                    "¿Qué hiciste primero para ordenar las figuras en tu mesa?",
                    "¿Cómo te diste cuenta de que el total siempre tiene más elementos que solo una parte?"
                ],
                "keywords": "pensamos en lo que aprendimos, cómo lograste agrupar, conté, comparé",
                "solution_detail": "Reflexión del estudiante sobre agrupación, conteo y relación parte-todo."
            }
        ]
    },
    {
        "page_number": 8,
        "challenge_title": "Reto 2: Rotulamos las cajas",
        "topic": "Reglas del juego de azar con moneda y tarjetas",
        "visual_context": "¿Qué se necesita?. Materiales: 20 tarjetas de cartulina con figuras (frutas o animales) y una moneda de 20 céntimos. ¿Cómo se juega?: Si sale Cara -> toma 1 tarjeta. Si sale Sello -> toma 2 tarjetas iguales. Se juegan 5 rondas. Gana quien acumule más tarjetas.",
        "pedagogical_goal": "Comprender reglas de juego y condiciones de probabilidad/azar.",
        "exercises": [
            {
                "exercise_order": 1,
                "dimension_id": "DIM-01",
                "question_text": "¿Cuáles son las reglas del juego de la moneda y las tarjetas? ¿Qué se escoge si sale cara y qué si sale sello?",
                "expected_concept": "Cara: escoger 1 tarjeta. Sello: escoger 2 tarjetas iguales. Se juegan 5 rondas y gana quien junte más tarjetas.",
                "socratic_hints": [
                    "¿Qué debes hacer cuando la moneda cae en cara?",
                    "¿Y si cae sello, cuántas tarjetas debes tomar y cómo tienen que ser?",
                    "¿Quién es el ganador al final de las 5 rondas?"
                ],
                "keywords": "reglas, moneda, cara, sello, 1 tarjeta, 2 tarjetas iguales",
                "solution_detail": "Cara = 1 tarjeta; Sello = 2 tarjetas iguales; 5 rondas; gana quien acumule más."
            }
        ]
    },
    {
        "page_number": 9,
        "challenge_title": "Reto 2: Rotulamos las cajas",
        "topic": "Juego práctico con tarjetas de frutas y registro de resultados",
        "visual_context": "Muestra 20 tarjetas de frutas: 2 manzanas rojas, 5 peras verdes, 6 naranjas, 7 plátanos. Total de tarjetas elaboradas = 20. Espacios para registrar las tarjetas ganadas por el niño y su compañero, y preguntas de comparación.",
        "pedagogical_goal": "Registrar cantidades en tablas simples y comparar datos obtenidos en un juego.",
        "exercises": [
            {
                "exercise_order": 1,
                "dimension_id": "DIM-01",
                "question_text": "¿Cuántas tarjetas de frutas elaboraron en total y cuántas de cada fruta?",
                "expected_concept": "Elaboraron 20 tarjetas en total: 2 manzanas rojas, 5 peras verdes, 6 naranjas y 7 plátanos.",
                "socratic_hints": [
                    "Contemos las tarjetas por fruta: ¿cuántas manzanas, peras, naranjas y plátanos hay?",
                    "Si sumas 2 + 5 + 6 + 7, ¿cuántas tarjetas prepararon en total?"
                ],
                "keywords": "tarjetas de frutas, cuántas elaboraron, 20 tarjetas, manzanas, peras, naranjas, plátanos",
                "solution_detail": "Total 20 tarjetas: 2 manzanas, 5 peras, 6 naranjas y 7 plátanos."
            },
            {
                "exercise_order": 2,
                "dimension_id": "DIM-02",
                "question_text": "¿De qué tarjetas hay mayor cantidad: de las tarjetas elaboradas o de las que lograron acumular en el juego?",
                "expected_concept": "Hay mayor cantidad de las tarjetas elaboradas en total (20 tarjetas elaboradas siempre es mayor que las tarjetas ganadas en las rondas).",
                "socratic_hints": [
                    "¿Cuántas tarjetas prepararon en total antes de jugar? (Eran 20).",
                    "¿Cuántas lograron ganar jugando las rondas?",
                    "¿Qué número es mayor: todas las que prepararon o solo las que ganaron?"
                ],
                "keywords": "mayor cantidad, tarjetas elaboradas, tarjetas acumuladas, elaboradas",
                "solution_detail": "De las tarjetas elaboradas en total (el todo es mayor que la parte acumulada)."
            }
        ]
    },
    {
        "page_number": 10,
        "challenge_title": "Reto 2: Rotulamos las cajas",
        "topic": "Simulación con tarjetas de animales y Ronda 1 (Lucía)",
        "visual_context": "Lucía y Paco dibujaron tarjetas de animales: 2 gallos, 5 gatos, 4 vacas y 7 perros (Total = 18 tarjetas). Lucía lanza la moneda y sale 'cara'. Paco le recuerda: 'Salió cara, entonces solo puedes tomar 1 figura de animal'. Lucía toma 1 gallo. Quedan en la mesa: 1 gallo, 5 gatos, 4 vacas y 7 perros (17 tarjetas).",
        "pedagogical_goal": "Realizar conteo inicial de colección heterogénea y aplicar la regla condicional del juego.",
        "exercises": [
            {
                "exercise_order": 1,
                "dimension_id": "DIM-01",
                "question_text": "¿Qué tarjetas elaboraron? ¿Cuántas tarjetas de animales elaboraron en total y cuántas por cada animal?",
                "expected_concept": "Elaboraron 18 tarjetas en total: 2 gallos, 5 gatos, 4 vacas y 7 perros.",
                "socratic_hints": [
                    "Cuenta cada animalito en los dibujos: ¿cuántos gallos, gatos, vacas y perros hay?",
                    "Si sumas 2 gallos + 5 gatos + 4 vacas + 7 perros, ¿cuántas tarjetas elaboraron en total?"
                ],
                "keywords": "tarjetas de animales, elaboraron en total, 18 tarjetas, gallos, gatos, vacas, perros",
                "solution_detail": "Total 18 tarjetas: 2 gallos, 5 gatos, 4 vacas y 7 perros."
            },
            {
                "exercise_order": 2,
                "dimension_id": "DIM-04",
                "question_text": "Lucía lanza la moneda y le sale 'cara'. ¿Qué figura toma y cuántas tarjetas quedan en la mesa?",
                "expected_concept": "Al salir cara toma 1 figura (elige 1 gallo). En la mesa quedan 17 tarjetas.",
                "socratic_hints": [
                    "Cuando la moneda sale cara, ¿cuántas tarjetas permite tomar la regla?",
                    "Lucía tomó 1 gallo. Si al inicio había 18 tarjetas, ¿cuántas quedan en la mesa?"
                ],
                "keywords": "Lucía lanza moneda, sale cara, toma 1 gallo, quedan 17",
                "solution_detail": "Toma 1 gallo. Quedan 17 tarjetas en la mesa."
            }
        ]
    },
    {
        "page_number": 11,
        "challenge_title": "Reto 2: Rotulamos las cajas",
        "topic": "Ronda de Paco (sello) y restricciones lógicas de selección",
        "visual_context": "Turno de Paco: lanza la moneda y sale 'sello'. Lucía le indica: 'Salió sello, entonces, puedes tomar 2 figuras, pero del mismo animalito'. Paco responde: 'Tomaré 2 figuras de vaquita'. Al lado se muestran las 2 tarjetas de vacas que toma Paco, y en el grupo restante quedan: 1 gallo, 5 gatos, 2 vacas y 7 perros (15 tarjetas en total). Al pie de página se indica que culminaron el juego tras lanzar la moneda 5 veces, quedando algunas tarjetas de animalitos.",
        "pedagogical_goal": "Analizar la disponibilidad y cantidad de elementos de una colección para cumplir condiciones lógicas restrictivas (seleccionar dos elementos iguales a partir del resultado 'sello').",
        "exercises": [
            {
                "exercise_order": 1,
                "dimension_id": "DIM-01",
                "question_text": "Observa las tarjetas que tenían Lucía y Paco. - ¿Cuántas tarjetas de gallo quedan?",
                "expected_concept": "Queda 1 tarjeta de gallo en la mesa.",
                "socratic_hints": [
                    "Había 2 gallos y Lucía ya tomó uno en el turno anterior.",
                    "Mira las tarjetas que quedan sobre la mesa: ¿cuántos gallos ves?"
                ],
                "keywords": "cuántas tarjetas de gallo quedan, gallo, queda 1, 1 tarjeta de gallo",
                "solution_detail": "Queda 1 tarjeta de gallo."
            },
            {
                "exercise_order": 2,
                "dimension_id": "DIM-04",
                "question_text": "¿Paco podría haber escogido 2 figuras de gallo?, ¿por qué?",
                "expected_concept": "No, porque la regla al salir sello exige tomar 2 figuras del mismo animalito y sobre la mesa solo queda 1 tarjeta de gallo.",
                "socratic_hints": [
                    "¿Cuántas tarjetas de gallo quedan disponibles en la mesa? (Solo 1).",
                    "¿Cuántas tarjetas iguales exige tomar la regla cuando sale sello?",
                    "¿Alcanzan los gallos para que Paco tome dos iguales?"
                ],
                "keywords": "Paco, 2 figuras de gallo, no podría, solo queda 1 gallo, regla de sello",
                "solution_detail": "No, porque solo queda 1 tarjeta de gallo y la regla exige tomar 2 figuras del mismo animal."
            },
            {
                "exercise_order": 3,
                "dimension_id": "DIM-04",
                "question_text": "¿Qué otras 2 tarjetas de animalitos podría haber escogido Paco?, ¿por qué?",
                "expected_concept": "Paco podría haber escogido 2 figuras de gato o 2 figuras de perro (o vacas), porque de esos animales había 2 o más tarjetas disponibles en la mesa.",
                "socratic_hints": [
                    "Fíjate en los animales que tienen 2 o más tarjetas en la mesa.",
                    "¿De cuáles animalitos hay suficiente cantidad para poder tomar una pareja?",
                    "¿Cuántos gatos y cuántos perros hay disponibles?"
                ],
                "keywords": "otras 2 tarjetas, gatos, perros, vacas, suficientes tarjetas, parejas",
                "solution_detail": "Podría haber escogido 2 figuras de gato o 2 de perro, porque quedaban 5 gatos y 7 perros (además de vacas)."
            }
        ]
    },
    {
        "page_number": 12,
        "challenge_title": "Reto 2: Rotulamos las cajas",
        "topic": "Conteo final, rotulación de cajas y metacognición",
        "visual_context": "Lucía y Paco muestran las tarjetas acumuladas. Lucía tiene 8 tarjetas (1 gallo, 3 gatos, 1 vaca, 3 perros) y Paco tiene 7 tarjetas (3 perros, 1 gato, 3 vacas). Cada niño sostiene una caja con un recuadro en blanco para rotular. Debajo hay enunciados amarillos para completar y la pregunta sobre si usaron todas las tarjetas. Al pie, el recuadro 'Pensamos en lo que aprendimos'.",
        "pedagogical_goal": "Contar y comparar colecciones, rotular cantidades, diferenciar el total de tarjetas elaboradas (18) del total acumulado (15), y reflexionar sobre el juego.",
        "exercises": [
            {
                "exercise_order": 1,
                "dimension_id": "DIM-05",
                "question_text": "Observa y escribe: Lucía y Paco colocaron las tarjetas en una cajita y contaron la cantidad que obtuvo cada uno. Como sabemos, la ganadora o el ganador del juego es quien ha acumulado más tarjetas. ¿Quién crees que ganó? ¿Por qué crees que ganó?",
                "expected_concept": "Lucía ganó porque acumuló 8 tarjetas y Paco obtuvo 7 (8 es mayor que 7). Debajo de Lucía se escribe '8 animales' y debajo de Paco '7 animales'.",
                "socratic_hints": [
                    "Cuenta una por una las tarjetas de animalitos que tiene Lucía.",
                    "Ahora cuenta cuántas tarjetas acumuló Paco en su grupo.",
                    "¿Cuál número es más grande: el 8 de Lucía o el 7 de Paco?"
                ],
                "keywords": "ganador, ganadora, Lucía, Paco, 8 animales, 7 animales, mayor que, ganó Lucía",
                "solution_detail": "Debajo de Lucía se coloca '8 animales' y debajo de Paco '7 animales'. Ganó Lucía porque 8 > 7."
            },
            {
                "exercise_order": 2,
                "dimension_id": "DIM-01",
                "question_text": "Coloca en una cajita las cantidades de tarjetas y rotula las figuras de animalitos que Lucía y Paco ganaron: Lucía y Paco elaboraron ___ tarjetas para jugar. Paco ganó ___ tarjetas. Lucía ganó ___ tarjetas.",
                "expected_concept": "En los rótulos de las cajas se escribe 8 para Lucía y 7 para Paco. En los enunciados: elaboraron 18 tarjetas para jugar, Paco ganó 7 tarjetas y Lucía ganó 8 tarjetas.",
                "socratic_hints": [
                    "Revisa la página 10: allí dibujaron todos los animalitos antes de jugar. ¿Recuerdas que sumaban 18 en total?",
                    "¿Cuántas tarjetas contaste que ganó Paco en la parte de arriba?",
                    "¿Y cuántas tarjetas ganó Lucía para colocar en su rótulo?"
                ],
                "keywords": "rotulación, tarjetas elaboradas, 18 tarjetas, Paco ganó 7, Lucía ganó 8, cajas",
                "solution_detail": "Rótulos de las cajas: Lucía '8' y Paco '7'. Enunciados: Elaboraron 18 tarjetas para jugar; Paco ganó 7 tarjetas; Lucía ganó 8 tarjetas."
            },
            {
                "exercise_order": 3,
                "dimension_id": "DIM-04",
                "question_text": "¿Utilizaron todas las tarjetas que elaboraron? Explica.",
                "expected_concept": "No utilizaron todas las tarjetas. Elaboraron 18 en total y entre los dos solo acumularon 15 (8 + 7 = 15), por lo que sobraron 3 tarjetas en la mesa.",
                "socratic_hints": [
                    "Suma las tarjetas que ganaron: 8 de Lucía + 7 de Paco. ¿Cuánto da esa suma?",
                    "Compara ese 15 con las 18 tarjetas que prepararon en la página 10.",
                    "¿Se usaron todas o quedó alguna tarjeta sin repartir?"
                ],
                "keywords": "utilizaron todas, no utilizaron todas, sobraron tarjetas, 18 menos 15, sobraron 3",
                "solution_detail": "No se utilizaron todas, porque elaboraron 18 y solo ganaron 15 (8 + 7 = 15). Sobraron 3 tarjetas sin ganar."
            },
            {
                "exercise_order": 4,
                "dimension_id": "DIM-06",
                "question_text": "Pensamos en lo que aprendimos: responde las preguntas de reflexión y metacognición.",
                "expected_concept": "El estudiante reflexiona sobre su proceso: cómo eligió las tarjetas, por qué con 9 tarjetas no alcanzaría para turnos pares equitativos, sugerencias para el juego y autoevaluación.",
                "socratic_hints": [
                    "¿Qué regla tuviste en cuenta cada vez que la moneda caía en cara o sello?",
                    "Si solo hubieran preparado 9 tarjetas en total, ¿habrían alcanzado para jugar 5 rondas completas?",
                    "¿Qué parte de este reto te pareció más difícil y cómo la resolviste?"
                ],
                "keywords": "pensamos en lo que aprendimos, 9 tarjetas, cambiar regla, dificultades, reflexión",
                "solution_detail": "Respuestas reflexivas del estudiante analizando paridad, suficiencia de tarjetas y estrategias de conteo."
            }
        ]
    }
]

class CurriculumDB:
    """Administrador de la base de datos SQLite y del Temario estructurado para el Tutor Socrático"""
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de Páginas
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                page_number INTEGER PRIMARY KEY,
                challenge_title TEXT NOT NULL,
                topic TEXT NOT NULL,
                visual_context TEXT NOT NULL,
                pedagogical_goal TEXT NOT NULL
            );
            """)

            # Tabla de Ejercicios
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_number INTEGER NOT NULL,
                exercise_order INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                expected_concept TEXT NOT NULL,
                socratic_hints TEXT NOT NULL,
                keywords TEXT NOT NULL,
                solution_detail TEXT NOT NULL,
                dimension_id TEXT DEFAULT 'DIM-01',
                FOREIGN KEY(page_number) REFERENCES pages(page_number)
            );
            """)

            # Auto-migración si no existe dimension_id
            cursor.execute("PRAGMA table_info(exercises)")
            cols = [row[1] for row in cursor.fetchall()]
            if "dimension_id" not in cols:
                cursor.execute("ALTER TABLE exercises ADD COLUMN dimension_id TEXT DEFAULT 'DIM-01'")

            # Tabla de Sesión del Estudiante (Progreso en tiempo real)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_session (
                session_id TEXT PRIMARY KEY,
                current_page INTEGER DEFAULT NULL,
                current_exercise_id INTEGER,
                completed_exercises TEXT DEFAULT '[]',
                notes TEXT DEFAULT '',
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            conn.commit()

            # Verificar si ya existen datos o poblarlos
            cursor.execute("SELECT COUNT(*) as count FROM pages")
            row = cursor.fetchone()
            if row["count"] == 0:
                self._seed_data(conn)

    def reseed(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS exercises")
            cursor.execute("DROP TABLE IF EXISTS pages")
            cursor.execute("DROP TABLE IF EXISTS student_session")
            conn.commit()
            self._init_db()

    def reset_session(self, session_id: str = "default"):
        """Reinicia el estado de la sesión para iniciar sin página predeterminada fija"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO student_session (session_id, current_page, current_exercise_id, completed_exercises, last_interaction)
            VALUES (?, NULL, NULL, '[]', CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                current_page = NULL,
                current_exercise_id = NULL,
                completed_exercises = '[]',
                last_interaction = CURRENT_TIMESTAMP
            """, (session_id,))
            conn.commit()

    def _seed_data(self, conn: sqlite3.Connection):
        cursor = conn.cursor()
        for p in CURRICULUM_DATA:
            cursor.execute("""
            INSERT INTO pages (page_number, challenge_title, topic, visual_context, pedagogical_goal)
            VALUES (?, ?, ?, ?, ?)
            """, (p["page_number"], p["challenge_title"], p["topic"], p["visual_context"], p["pedagogical_goal"]))

            for ex in p.get("exercises", []):
                cursor.execute("""
                INSERT INTO exercises (page_number, exercise_order, question_text, expected_concept, socratic_hints, keywords, solution_detail, dimension_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p["page_number"],
                    ex["exercise_order"],
                    ex["question_text"],
                    ex["expected_concept"],
                    json.dumps(ex["socratic_hints"], ensure_ascii=False),
                    ex["keywords"],
                    ex["solution_detail"],
                    ex.get("dimension_id", "DIM-01")
                ))
        
        cursor.execute("""
        INSERT OR IGNORE INTO student_session (session_id, current_page, completed_exercises)
        VALUES ('default', NULL, '[]')
        """)
        conn.commit()

    def get_page(self, page_number: Optional[int]) -> Optional[Dict[str, Any]]:
        if not page_number:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pages WHERE page_number = ?", (page_number,))
            row = cursor.fetchone()
            if not row:
                return None
            
            page = dict(row)
            cursor.execute("SELECT * FROM exercises WHERE page_number = ? ORDER BY exercise_order ASC", (page_number,))
            page["exercises"] = [dict(r) for r in cursor.fetchall()]
            for ex in page["exercises"]:
                ex["socratic_hints"] = json.loads(ex["socratic_hints"])
            return page

    def get_all_pages(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pages ORDER BY page_number ASC")
            pages = [dict(r) for r in cursor.fetchall()]
            for p in pages:
                cursor.execute("SELECT * FROM exercises WHERE page_number = ? ORDER BY exercise_order ASC", (p["page_number"],))
                p["exercises"] = [dict(r) for r in cursor.fetchall()]
                for ex in p["exercises"]:
                    ex["socratic_hints"] = json.loads(ex["socratic_hints"])
            return pages

    def get_session(self, session_id: str = "default") -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM student_session WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                data = dict(row)
                data["completed_exercises"] = json.loads(data["completed_exercises"]) if data.get("completed_exercises") else []
                return data
            return {"session_id": session_id, "current_page": None, "current_exercise_id": None, "completed_exercises": []}

    def set_current_page(self, page_number: int, session_id: str = "default"):
        if page_number < 1 or page_number > 12:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO student_session (session_id, current_page, last_interaction)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                current_page = excluded.current_page,
                last_interaction = CURRENT_TIMESTAMP
            """, (session_id, page_number))
            conn.commit()

    def get_full_curriculum_prompt(self) -> str:
        """
        Genera el temario completo y estructurado del Cuadernillo para conocimiento
        directo del LLM (cero regex, navegación por juicio y razonamiento del modelo).
        """
        lines = [
            "📚 TEMARIO Y CUADERNILLO ESCOLAR OFICIAL (Resolvemos problemas jugando 2):",
            "El cuadernillo contiene 2 grandes Retos organizados por páginas. Utiliza tu propio juicio y entendimiento del contexto para identificar en qué reto, página o ejercicio está el estudiante según lo que te converse:\n"
        ]

        pages = self.get_all_pages()
        for p in pages:
            lines.append(f"--- [PÁGINA {p['page_number']}: {p['challenge_title']} | Tema: {p['topic']}] ---")
            lines.append(f"• Lo que el niño ve en la página: {p['visual_context']}")
            lines.append(f"• Objetivo pedagógico: {p['pedagogical_goal']}")
            
            if p.get("exercises"):
                lines.append("• Ejercicios y preguntas de esta página:")
                for ex in p["exercises"]:
                    dim = ex.get("dimension_id", "DIM-01")
                    hints_str = " | ".join(ex.get("socratic_hints", []))
                    lines.append(f"   - Pregunta {ex['exercise_order']} ({dim}): \"{ex['question_text']}\"")
                    lines.append(f"     * Concepto/Respuesta esperada: {ex['expected_concept']}")
                    lines.append(f"     * Pistas socráticas sugeridas: {hints_str}")
            lines.append("")

        # Marco teórico general de Pensamiento Crítico
        lines.append(pc_theory.get_prompt_evaluation_scaffolding(None))
        return "\n".join(lines)

# Instancia global disponible para importar
curriculum = CurriculumDB()

if __name__ == "__main__":
    print("🔄 Reindexando y poblando la base de datos SQLite 'curriculum.db'...")
    curriculum.reseed()
    pages = curriculum.get_all_pages()
    total_exercises = sum(len(p.get("exercises", [])) for p in pages)
    print(f"✅ ¡Base de datos reindexada con éxito!")
    print(f"📖 Total de páginas: {len(pages)} | 🎯 Total de ejercicios cargados: {total_exercises}\n")
