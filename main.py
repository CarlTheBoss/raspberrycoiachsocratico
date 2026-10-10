import sys
import time
import queue
import threading
from colorama import Fore, Style, init
from config import GEMINI_API_KEY, FISH_AUDIO_API_KEY, GROQ_API_KEY, GPIO_BUTTON_PIN
from audio_io import AudioRecorder, has_wake_word, extract_message_after_wake_word, is_stop_command, is_exit_command
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
    print(f"{Fore.CYAN} 🤖 ROBOT COACH SOCRÁTICO (Activación e Interrupción por 'Elena') 🤖{Style.RESET_ALL}")
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
    current_page = coach.get_current_page()
    print(f"{Fore.CYAN}📖 Cuadernillo escolar cargado en SQLite: Página actual -> {current_page}{Style.RESET_ALL}")
    saludo_inicial = f"¡Hola! Soy Elena, tu compañera de tareas. Para hablar conmigo, solo di mi nombre: Elena, y dime qué duda tienes."
    print(f"\n{Fore.MAGENTA}🤖 Elena: {saludo_inicial}{Style.RESET_ALL}")
    tts.speak(saludo_inicial)

    print(f"\n{Fore.GREEN}🟢 Elena está lista. Solo responderá y se interrumpirá cuando digas 'Elena'. (Ctrl+C para apagar){Style.RESET_ALL}\n")

    next_user_text = None

    try:
        while True:
            # 1. Obtener mensaje del niño (capturado por interrupción previa o nuevo turno)
            if next_user_text:
                user_text = next_user_text
                next_user_text = None
            else:
                if button_pin is not None:
                    import RPi.GPIO as GPIO
                    print(f"{Fore.BLUE}👉 Presiona el botón del robot para hablar...{Style.RESET_ALL}")
                    while GPIO.input(button_pin) == GPIO.HIGH:
                        time.sleep(0.05)
                    print(f"{Fore.GREEN}🟢 ¡Botón presionado! Te escucho...{Style.RESET_ALL}")

                print(f"\n{Fore.BLUE}👂 Esperando que digas 'Elena...' (solo hablo si me llamas){Style.RESET_ALL}")
                audio_data = recorder.record_until_silence()

                if len(audio_data) == 0:
                    continue

                # 2. Transcripción instantánea con Groq Whisper
                print(f"{Fore.YELLOW}⏳ Transcribiendo voz...{Style.RESET_ALL}")
                user_text = stt.transcribe(audio_data)

                if not user_text:
                    continue

                # Verificar si llamó a Elena o dio orden de detención/salida
                if not has_wake_word(user_text) and not is_stop_command(user_text) and not is_exit_command(user_text):
                    print(f"{Fore.YELLOW}ℹ️ [Ignorado: \"{user_text}\" - No mencionaste 'Elena']{Style.RESET_ALL}")
                    continue

            print(f"{Fore.CYAN}👦 Niño: {user_text}{Style.RESET_ALL}")

            # Manejo directo si el niño pide salir / cerrar la sesión
            if is_exit_command(user_text):
                msg_despedida = "¡Hasta luego! Hiciste un gran trabajo hoy. ¡Adiós!"
                print(f"{Fore.MAGENTA}🤖 Elena: {msg_despedida}{Style.RESET_ALL}")
                tts.speak(msg_despedida)
                break

            # Manejo directo si el niño pide pausa en su turno
            if is_stop_command(user_text):
                msg_pausa = "¡Entendido! Hacemos una pausa. Cuando me necesites, solo llámame diciendo Elena."
                print(f"{Fore.MAGENTA}🤖 Elena: {msg_pausa}{Style.RESET_ALL}")
                tts.speak(msg_pausa)
                continue

            # 3. Turno de Elena: Streaming de Oraciones + Reproducción Continua
            print(f"{Fore.MAGENTA}🤖 Elena: {Style.RESET_ALL}", end="", flush=True)
            
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

            # Reproducir audio de Elena. Si el niño interrumpe diciendo 'Elena [mensaje]',
            # play_audio_queue captura y retorna esa nueva frase de inmediato
            interrupted_text = recorder.play_audio_queue(
                audio_queue=audio_queue,
                stop_event=stop_event,
                stt_transcribe_func=stt.transcribe
            )

            # Asegurar que el hilo productor finalice
            stop_event.set()
            print(f"\n{Style.RESET_ALL}" + "-" * 50)

            if interrupted_text:
                next_user_text = interrupted_text

    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🔴 Apagando el robot... ¡Hasta la próxima! 👋{Style.RESET_ALL}")
        tts.speak("¡Hasta luego! Hiciste un gran trabajo hoy.")
    finally:
        # Limpiar el archivo episodic_memory.json al cerrar
        coach.memory.clear_memory()
        if button_pin is not None:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass

if __name__ == "__main__":
    main()
