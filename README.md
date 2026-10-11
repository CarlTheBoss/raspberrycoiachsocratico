# 🤖 Robot Coach Socrático para Niños ("Elena") 🚀
> **Asistente de voz interactivo con Google Gemini, Fish Audio S2.1 Pro TTS, Deepgram Nova-3 / Groq Whisper STT, SQLite Curricular y Push-to-Talk.**

Elena es una robot tutora amigable y pedagógica diseñada para ayudar a niños con sus tareas escolares usando el **método socrático**: jamás da la respuesta directa, sino que guía al niño con preguntas amigables, pistas y ejemplos cotidianos.

---

## ✨ Características Principales

- 🎙️ **Oído Inteligente Multi-Proveedor (STT):** Transcripción ultra-rápida con **Deepgram Nova-3** (~150ms), **Gemini Transcribe** (`gemini-3.5-transcribe`), y fallback automático con **Groq Whisper** (`whisper-large-v3-turbo`).
- 🧠 **Cerebro Pedagógico (LLM):** **Google Gemini 2.5 Flash** con prompt socrático infantil estricto, interactivo y motivador.
- 🔊 **Voz Expresiva (TTS):** **Fish Audio S2.1 Pro** con voz natural, cálida y consistente en español.
- 🔘 **Push-to-Talk Físico y en PC:** Soporta botón arcade físico en Raspberry Pi (GPIO) o modo Push-to-Talk en PC manteniendo presionado `[ESPACIO]`.
- 🛑 **Interrupción Fluida (Barge-in):** Si Elena está hablando y el niño pulsa el botón o dice *"Elena..."*, el robot se detiene al instante y escucha de inmediato.
- ⚡ **Streaming de Oraciones con Precarga (*Zero-Delay*):** Productor-consumidor en paralelo para eliminar pausas entre frases.
- 💾 **Memoria Episódica Persistente:** Recuerda el nombre, gustos, temas practicados y dudas del niño entre sesiones en segundo plano.
- 📚 **Base Curricular en SQLite (`curriculum.db`):** Sabe exactamente en qué página y ejercicio del cuadernillo escolar está el niño, qué figuras está viendo y le da pistas socráticas precisas sin revelar la solución.
- 🔌 **Auto-arranque en Raspberry Pi:** Configurado como servicio `systemd` para encenderse solo al conectar a la corriente.

---

## 📁 Estructura del Repositorio

```text
robot-coach-kids/
├── .env.example            # Plantilla de variables de entorno y API Keys
├── .gitignore              # Protección para no subir claves ni entornos
├── config.py               # Configuración de audio, modelos y claves
├── curriculum.db           # Base de datos SQLite del cuadernillo escolar
├── curriculum_db.py        # Gestor de búsqueda contextual y socrática del cuadernillo
├── prompt.py               # System Prompt del tutor socrático ("Elena")
├── stt.py                  # Reconocimiento de voz Multi-STT (Deepgram, Gemini, Groq)
├── llm.py                  # Razonamiento socrático con Gemini + Streaming + SQLite
├── tts.py                  # Generación de voz con Fish Audio S2.1 Pro
├── memory.py               # Memoria episódica persistente y asíncrona
├── audio_io.py             # Grabación, VAD, Push-to-Talk y reproductor con Barge-in
├── main.py                 # Orquestador del bucle conversacional
└── requirements.txt        # Dependencias de Python
```

---

## 🛠️ Requisitos de Hardware (Raspberry Pi)

1. **Raspberry Pi 4 o 5** con **Raspberry Pi OS (64-bit)**.
2. **Tarjeta MicroSD** (mínimo 16GB / 32GB).
3. **Micrófono USB** (o tarjeta HAT de audio tipo ReSpeaker).
4. **Parlante** (Jack 3.5mm, USB o mini-amplificador).
5. *(Opcional)* **Pulsador/Botón físico** conectado a un pin GPIO (ej. GPIO 17).

---

## 🚀 Guía de Instalación Paso a Paso en Raspberry Pi

### 1. Preparar el Sistema Operativo (desde tu PC)
1. Usa **[Raspberry Pi Imager](https://www.raspberrypi.com/software/)** para grabar **Raspberry Pi OS (64-bit)** en tu MicroSD.
2. En los ajustes (`Ctrl + Shift + X`), configura tu red Wi-Fi, usuario (`pi`) y habilita **SSH**.
3. Inserta la MicroSD en la Raspberry Pi, conecta micrófono, parlante y enciéndela.

### 2. Conectarte por SSH a la Raspberry Pi
Desde tu laptop:
```bash
ssh pi@raspberrypi.local
```

### 3. Instalar librerías del sistema de audio y C
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git portaudio19-dev libasound2-dev libportaudio2 ffmpeg
```

### 4. Clonar el repositorio
```bash
git clone https://github.com/CarlTheBoss/raspberrycoiachsocratico.git
cd raspberrycoiachsocratico
```

### 5. Crear el entorno virtual e instalar dependencias
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Configurar tus API Keys
Crea tu archivo `.env` a partir de la plantilla:
```bash
cp .env.example .env
nano .env
```

Configura tus credenciales:
```env
# 1. Google Gemini (Gratis en https://aistudio.google.com/)
GEMINI_API_KEY=tu_gemini_api_key_aqui

# 2. Fish Audio (https://fish.audio/app/api-keys/)
FISH_AUDIO_API_KEY=tu_fish_audio_api_key_aqui

# 3. Groq API (Gratis en https://console.groq.com/)
GROQ_API_KEY=tu_groq_api_key_aqui

# (Opcional) ID de voz fija de Fish Audio desde https://fish.audio/discovery
FISH_REFERENCE_ID=
```
*Guarda con `Ctrl + O`, presiona `Enter` y sal con `Ctrl + X`.*

---

## 🎙️ Ejecutar el Robot

Para iniciar a Tobi:
```bash
python main.py
```

---

## ⚡ Encendido Automático al Conectar a la Corriente (Servicio Systemd)

Para que el robot arranque solo cada vez que se conecta a la fuente de poder sin necesidad de usar pantallas ni terminales:

1. Crea el archivo del servicio:
```bash
sudo nano /etc/systemd/system/tobi-robot.service
```

2. Pega la siguiente configuración (ajusta la ruta según tu usuario):
```ini
[Unit]
Description=Robot Tobi Coach Socratico para Ninos
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/raspberrycoiachsocratico
ExecStart=/home/pi/raspberrycoiachsocratico/venv/bin/python main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

3. Activa e inicia el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tobi-robot.service
sudo systemctl start tobi-robot.service
```

4. Ver el estado del robot:
```bash
sudo systemctl status tobi-robot.service
```

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Diseñado para fines educativos y desarrollo de agentes de IA con hardware embebido.
