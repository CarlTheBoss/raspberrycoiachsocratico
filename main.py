import sys
import time
import queue
import threading
from colorama import Fore, Style, init
from config import GEMINI_API_KEY, FISH_AUDIO_API_KEY, GROQ_API_KEY, GPIO_BUTTON_PIN
from audio_io import AudioRecorder
from stt import SpeechToText
from llm import SocraticCoach
from tts import TextToSpeech

init(autoreset=True)

def setup_gpio_button():
    """Configura el botón GPIO si corre en una Raspberry Pi real"""
    if not GPIO_BUTTON_PIN:
        return None
    try:
        import RPi.GPIO as GPIO
        pin = int(GPIO_BUTTON_PIN)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        print(f"{Fore.GREEN}✅ Botón físico GPIO configurado en el Pin {pin}{Style.RESET_ALL}")
        return pin
    except ImportError:
        print(f"{Fore.YELLOW}ℹ️ RPi.GPIO no disponible. Modo micrófono continuo activado.{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error al configurar GPIO: {e}{Style.RESET_ALL}")
        return None

def main():
    print(f"\n{Fore.CYAN}==================================================================={Style.RESET_ALL}")
    print(f"{Fore.CYAN} 🤖 ROBOT COACH SOCRÁTICO (Streaming Continuo sin Pausas) 🤖{Style.RESET_ALL}")
    print(f"{Fore.CYAN}===================================================================\n{Style.RESET_ALL}")

    # Validar API Keys
    missing_keys = []
    if not GEMINI_API_KEY:
        missing_keys.append("GEMINI_API_KEY (Google AI Studio)")
    if not FISH_AUDIO_API_KEY:
        missing_keys.append("FISH_AUDIO_API_KEY (Fish Audio)")
    if not GROQ_API_KEY:
        missing_keys.append("GROQ_API_KEY (Groq Console)")

    if missing_keys:
        print(f"{Fore.RED}❌ Error: Faltan las siguientes API Keys en tu archivo .env:{Style.RESET_ALL}")
        for k in missing_keys:
            print(f"  - {k}")
        print(f"\n{Fore.YELLOW}Añádelas en el archivo .env y vuelve a iniciar.{Style.RESET_ALL}\n")
        sys.exit(1)

    print(f"{Fore.YELLOW}⚡ Inicializando módulos con Pipeline de Precarga Continua...{Style.RESET_ALL}")
    recorder = AudioRecorder()
    stt = SpeechToText()
    coach = SocraticCoach()
    tts = TextToSpeech()
    button_pin = setup_gpio_button()

    # Saludo de bienvenida
    saludo_inicial = "¡Hola! Soy Tobi, tu compañero de tareas. ¿En qué problema o tarea quieres que trabajemos hoy?"
    print(f"\n{Fore.MAGENTA}🤖 Tobi: {saludo_inicial}{Style.RESET_ALL}")
    tts.speak(saludo_inicial)

    print(f"\n{Fore.GREEN}🟢 Tobi está listo y escuchando. (Presiona Ctrl+C para apagar){Style.RESET_ALL}\n")

    pending_audio = None

    try:
        while True:
            # 1. Capturar voz del niño
            if pending_audio is not None and len(pending_audio) > 0:
                audio_data = pending_audio
                pending_audio = None
            else:
                if button_pin is not None:
                    import RPi.GPIO as GPIO
                    print(f"{Fore.BLUE}👉 Presiona el botón del robot para hablar...{Style.RESET_ALL}")
                    while GPIO.input(button_pin) == GPIO.HIGH:
                        time.sleep(0.05)
                    print(f"{Fore.GREEN}🟢 ¡Botón presionado! Te escucho...{Style.RESET_ALL}")

                print(f"{Fore.BLUE}👂 Esperando que el niño hable...{Style.RESET_ALL}")
                audio_data = recorder.record_until_silence()

            if len(audio_data) == 0:
                continue

            # 2. Transcripción instantánea con Groq Whisper
            print(f"{Fore.YELLOW}⏳ Transcribiendo voz...{Style.RESET_ALL}")
            user_text = stt.transcribe(audio_data)

            if not user_text:
                continue

            print(f"{Fore.CYAN}👦 Niño: {user_text}{Style.RESET_ALL}")

            # 3. Pipeline de Precarga: Productor TTS en hilo paralelo + Reproductor continuo
            print(f"{Fore.MAGENTA}🤖 Tobi: {Style.RESET_ALL}", end="", flush=True)
            
            audio_queue = queue.Queue(maxsize=15)
            stop_event = threading.Event()

            def tts_producer():
                """Genera el audio de las siguientes oraciones en paralelo mientras la actual se reproduce"""
                try:
                    for sentence in coach.stream_sentences(user_text):
                        if stop_event.is_set():
                            break
                        if not sentence.strip():
                            continue
                        
                        audio_result = tts.generate_audio(sentence)
                        if audio_result and not stop_event.is_set():
                            audio_queue.put(audio_result)
                finally:
                    # Enviar señal de fin de generación
                    audio_queue.put(None)

            producer_thread = threading.Thread(target=tts_producer, daemon=True)
            producer_thread.start()

            # Reproducir audio desde la cola sin pausas entre oraciones
            pending_audio = recorder.play_audio_queue(audio_queue, stop_event)

            # Si terminó o fue interrumpido, asegurar que el hilo productor finalice
            stop_event.set()
            print(f"\n{Style.RESET_ALL}" + "-" * 50)

    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🔴 Apagando a Tobi... ¡Hasta la próxima! 👋{Style.RESET_ALL}")
        tts.speak("¡Hasta luego! Hiciste un gran trabajo hoy.")
    finally:
        if button_pin is not None:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass

if __name__ == "__main__":
    main()
