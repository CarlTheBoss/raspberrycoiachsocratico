import sys
import time
import queue
import threading
from typing import Optional
from colorama import Fore, Style, init
from config import (
    GEMINI_API_KEY, FISH_AUDIO_API_KEY, GROQ_API_KEY,
    DEEPGRAM_API_KEY, STT_PROVIDER, GPIO_BUTTON_PIN
)
from audio_io import AudioRecorder, has_wake_word, extract_message_after_wake_word, is_stop_command, is_exit_command
from stt import SpeechToText
from llm import SocraticCoach
from tts import TextToSpeech

init(autoreset=True)

def speak_interruptible(text: str, tts: TextToSpeech, recorder: AudioRecorder, stt: SpeechToText) -> Optional[str]:
    """Reproduce una frase de manera que el niño pueda interrumpirla diciendo 'Elena' o hablando"""
    print(f"\n{Fore.MAGENTA}🤖 Elena: {text}{Style.RESET_ALL}")
    q = queue.Queue(maxsize=5)
    stop = threading.Event()
    audio_res = tts.generate_audio(text)
    if audio_res:
        q.put(audio_res)
    q.put(None)
    interrupted = recorder.play_audio_queue(
        audio_queue=q,
        stop_event=stop,
        stt_transcribe_func=stt.transcribe
    )
    stop.set()
    return interrupted

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
    if not DEEPGRAM_API_KEY and not GROQ_API_KEY:
        missing_keys.append("DEEPGRAM_API_KEY o GROQ_API_KEY (Para reconocimiento de voz)")

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

    # Saludo de bienvenida interrumpible
    print(f"{Fore.CYAN}📖 Cuadernillo escolar cargado en SQLite: Búsqueda dinámica por intención activada 🧠{Style.RESET_ALL}")
    saludo_inicial = "¡Hola! Soy Elena, tu compañera de estudio. Para hablar conmigo, solo di mi nombre: Elena, y dime qué duda tienes."
    interrupted_startup = speak_interruptible(saludo_inicial, tts, recorder, stt)

    conversation_active = True
    next_user_text = interrupted_startup
    idle_silence_count = 0

    try:
        while True:
            # 1. Obtener mensaje del niño (capturado por interrupción previa o nuevo turno)
            if next_user_text:
                user_text = next_user_text
                next_user_text = None
                conversation_active = True
                idle_silence_count = 0
            else:
                if button_pin is not None:
                    import RPi.GPIO as GPIO
                    print(f"{Fore.BLUE}👉 Presiona el botón del robot para hablar...{Style.RESET_ALL}")
                    while GPIO.input(button_pin) == GPIO.HIGH:
                        time.sleep(0.05)
                    print(f"{Fore.GREEN}🟢 ¡Botón presionado! Te escucho...{Style.RESET_ALL}")

                if conversation_active:
                    recorder.play_listening_beep()
                    print(f"\n{Fore.BLUE}🔔 [pup] Te escucho... (o di 'Elena [mensaje]' / 'para'){Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.BLUE}👂 En espera... Di 'Elena' para hablar conmigo:{Style.RESET_ALL}")

                audio_data = recorder.record_until_silence()

                # Si no hubo audio o no se detectó voz
                if len(audio_data) == 0:
                    if conversation_active:
                        idle_silence_count += 1
                        if idle_silence_count == 1:
                            reprompt = "¡Hola! No logré escucharte bien. ¿Podrías repetirme lo que dijiste o necesitas una pista?"
                            interrupted = speak_interruptible(reprompt, tts, recorder, stt)
                            if interrupted:
                                next_user_text = interrupted
                            continue
                        elif idle_silence_count >= 2:
                            standby_msg = "Estaré aquí lista. Cuando quieras continuar, solo llámame diciendo Elena."
                            interrupted = speak_interruptible(standby_msg, tts, recorder, stt)
                            conversation_active = False
                            idle_silence_count = 0
                            if interrupted:
                                next_user_text = interrupted
                            continue
                    continue

                # 2. Transcripción instantánea con Groq Whisper
                print(f"{Fore.YELLOW}⏳ Transcribiendo voz...{Style.RESET_ALL}")
                user_text = stt.transcribe(audio_data)

                if not user_text:
                    if conversation_active:
                        idle_silence_count += 1
                        if idle_silence_count == 1:
                            reprompt = "No te escuchooo"
                            interrupted = speak_interruptible(reprompt, tts, recorder, stt)
                            if interrupted:
                                next_user_text = interrupted
                            continue
                        elif idle_silence_count >= 2:
                            standby_msg = "Estaré aquí lista. Cuando quieras continuar, solo llámame diciendo Elena."
                            interrupted = speak_interruptible(standby_msg, tts, recorder, stt)
                            conversation_active = False
                            idle_silence_count = 0
                            if interrupted:
                                next_user_text = interrupted
                            continue
                    continue

                # Si estamos en espera (no en conversación activa), exigir wake word
                if not conversation_active:
                    if not has_wake_word(user_text) and not is_exit_command(user_text):
                        print(f"{Fore.YELLOW}ℹ️ [Ignorado: \"{user_text}\" - Di 'Elena' para activarme]{Style.RESET_ALL}")
                        continue
                    else:
                        conversation_active = True

            # Resetear contador de silencios porque el niño habló
            idle_silence_count = 0
            print(f"{Fore.CYAN}👦 Niño: {user_text}{Style.RESET_ALL}")

            # Manejo directo si el niño pide salir / cerrar la sesión
            if is_exit_command(user_text):
                msg_despedida = "¡Hasta luego! Hiciste un gran trabajo hoy. ¡Adiós!"
                speak_interruptible(msg_despedida, tts, recorder, stt)
                break

            # Manejo directo si el niño pide pausa en su turno
            if is_stop_command(user_text):
                conversation_active = False
                idle_silence_count = 0
                msg_pausa = "¡Entendido! Hacemos una pausa. Cuando me necesites, solo llámame diciendo Elena."
                speak_interruptible(msg_pausa, tts, recorder, stt)
                continue

            conversation_active = True

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
        # Limpiar la memoria episódica y resetear sesión de página al cerrar
        coach.memory.clear_memory()
        coach.curriculum.reset_session()
        if button_pin is not None:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass

if __name__ == "__main__":
    main()
