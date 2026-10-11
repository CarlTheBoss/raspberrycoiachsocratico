import sys
import time
import queue
import threading
import select
import numpy as np
from typing import Optional, Callable
from colorama import Fore, Style, init
from config import (
    GEMINI_API_KEY, FISH_AUDIO_API_KEY, GROQ_API_KEY,
    DEEPGRAM_API_KEY, STT_PROVIDER, GPIO_BUTTON_PIN, SIMULATE_BUTTON_KEY
)
from audio_io import AudioRecorder, has_wake_word, extract_message_after_wake_word, is_stop_command, is_exit_command
from stt import SpeechToText
from llm import SocraticCoach
from tts import TextToSpeech

init(autoreset=True)

def speak_interruptible(
    text: str,
    tts: TextToSpeech,
    recorder: AudioRecorder,
    stt: SpeechToText,
    button_check_func: Optional[Callable[[], bool]] = None
) -> Optional[str]:
    """Reproduce una frase de manera que el niño pueda interrumpirla diciendo 'Elena' o presionando el botón"""
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
        stt_transcribe_func=stt.transcribe,
        button_check_func=button_check_func
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
    if STT_PROVIDER != "gemini" and not DEEPGRAM_API_KEY and not GROQ_API_KEY:
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

    # Simulación de botón por teclado (Terminal Linux) o GPIO real
    def flush_stdin():
        """Limpia cualquier tecla acumulada en el buffer para evitar cortes fantasmas"""
        if sys.stdin.isatty():
            try:
                import termios
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
            except Exception:
                pass

    # Configurar comprobación de estado físico de la tecla en PC (X11 / Terminal)
    x11_display = None
    space_keycode = 65
    try:
        import ctypes
        from ctypes import util
        lib_x11 = ctypes.cdll.LoadLibrary(util.find_library("X11"))
        if lib_x11:
            x11_display = lib_x11.XOpenDisplay(None)
            if x11_display:
                space_keycode = lib_x11.XKeysymToKeycode(x11_display, 0x0020)
    except Exception:
        x11_display = None

    def is_space_key_physically_down() -> bool:
        """Verifica en tiempo real si la tecla espacio está físicamente abajo (presionada)"""
        if x11_display is not None:
            try:
                keys_return = (ctypes.c_char * 32)()
                lib_x11.XQueryKeymap(x11_display, keys_return)
                byte_idx = space_keycode // 8
                bit_idx = space_keycode % 8
                byte_val = keys_return[byte_idx]
                if isinstance(byte_val, (str, bytes)):
                    byte_val = ord(byte_val) if isinstance(byte_val, str) else byte_val[0]
                return bool((byte_val >> bit_idx) & 1)
            except Exception:
                pass
        return False

    def check_keyboard_trigger() -> bool:
        """Comprueba si el usuario presionó una tecla en la terminal sin bloquear"""
        if not SIMULATE_BUTTON_KEY or not sys.stdin.isatty():
            return False
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.0)
            if rlist:
                ch = sys.stdin.read(1)
                flush_stdin()
                return True
        except Exception:
            pass
        return False

    def check_btn_pressed() -> bool:
        # 1. Comprobar botón GPIO físico en Raspberry Pi
        if button_pin is not None:
            try:
                import RPi.GPIO as GPIO
                return GPIO.input(button_pin) == GPIO.LOW  # LOW = presionado con pull-up
            except Exception:
                pass
        # 2. Comprobar tecla de espacio físicamente presionada en PC
        if is_space_key_physically_down():
            flush_stdin()
            return True
        # 3. Fallback por buffer de teclado
        return check_keyboard_trigger()

    def check_btn_released() -> bool:
        # En Raspberry Pi con botón físico: soltado = pin en HIGH
        if button_pin is not None:
            try:
                import RPi.GPIO as GPIO
                return GPIO.input(button_pin) == GPIO.HIGH  # HIGH = soltado con pull-up
            except Exception:
                pass
            return False

        # En PC: si tenemos estado físico de X11, verifica si soltó la tecla espacio
        if x11_display is not None:
            # Mientras la tecla espacio siga físicamente presionada, NO se suelta
            if is_space_key_physically_down():
                return False
            # La tecla espacio no está presionada: se soltó
            flush_stdin()
            return True

        # Fallback sin X11 (segunda pulsación en terminal)
        if SIMULATE_BUTTON_KEY:
            if time.time() - recording_start_ts < 0.8:
                flush_stdin()
                return False
            return check_keyboard_trigger()
        return False

    recording_start_ts = 0.0

    # Configurar terminal en modo cbreak para capturar teclas al instante
    old_term_settings = None
    if sys.stdin.isatty() and SIMULATE_BUTTON_KEY:
        try:
            import termios
            import tty
            old_term_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
            print(f"{Fore.CYAN}⌨️ [Modo Teclado PC]: Pulsa [ESPACIO/ENTER] para hablar, y vuelve a pulsar [ESPACIO/ENTER] para enviar de inmediato.{Style.RESET_ALL}")
        except Exception:
            pass

    # Al encender, mandamos un 'Hola' interno para que Elena genere su saludo natural
    print(f"{Fore.CYAN}📖 Cuadernillo escolar cargado en SQLite: Búsqueda dinámica por intención activada 🧠{Style.RESET_ALL}")
    recorder.play_listening_beep()

    conversation_active = True
    next_user_text = "Hola"
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
                # Si hay botón físico o simulación en PC por tecla:
                # Esperar a que el usuario presione para comenzar a grabar
                has_button_mode = (button_pin is not None) or bool(SIMULATE_BUTTON_KEY)

                if has_button_mode:
                    if button_pin is not None:
                        print(f"{Fore.BLUE}👉 Presiona y mantén presionado el botón del robot para hablar...{Style.RESET_ALL}")
                    else:
                        print(f"\n{Fore.BLUE}⌨️ Mantén presionado [ESPACIO] para hablar...{Style.RESET_ALL}")

                    while not check_btn_pressed():
                        time.sleep(0.04)

                    recorder.play_listening_beep()
                    flush_stdin()
                    if button_pin is not None:
                        print(f"{Fore.GREEN}🟢 ¡Botón presionado! Te escucho (suéltalo al terminar)...{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.GREEN}🎙️ ¡Grabando! Habla ahora... (Suelta [ESPACIO] al terminar para enviar){Style.RESET_ALL}")
                elif conversation_active:
                    recorder.play_listening_beep()
                    print(f"\n{Fore.BLUE}🔔 [pup] Te escucho... (o di 'Elena [mensaje]' / di 'para'){Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.BLUE}👂 En espera... Di 'Elena' para hablar conmigo:{Style.RESET_ALL}")

                # Grabar audio
                recording_start_ts = time.time()
                button_release_check = check_btn_released if has_button_mode else None
                audio_data = recorder.record_until_silence(
                    button_is_released_func=button_release_check
                )

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

                # 2. Transcripción instantánea con Groq Whisper / Deepgram
                duration_sec = len(audio_data) / recorder.sample_rate
                peak_energy = float(np.max(np.abs(audio_data))) if len(audio_data) > 0 else 0.0
                print(f"{Fore.YELLOW}⏳ Transcribiendo voz ({duration_sec:.1f}s capturados, volumen pico: {peak_energy:.4f})...{Style.RESET_ALL}")
                user_text = stt.transcribe(audio_data)

                if user_text:
                    recorder.play_transcription_done_beep()
                    print(f"{Fore.GREEN}🗣️ Niño dijo: \"{user_text}\"{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠️ No se reconoció texto (audio vacío, silencio o ininteligible){Style.RESET_ALL}")

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

            flush_stdin()

            # Reproducir audio de Elena. Se corta si el niño dice 'Elena', 'para' o si presiona [ESPACIO] / botón GPIO
            interrupted_text = recorder.play_audio_queue(
                audio_queue=audio_queue,
                stop_event=stop_event,
                stt_transcribe_func=stt.transcribe,
                button_check_func=check_btn_pressed
            )

            # Asegurar que el hilo productor finalice
            stop_event.set()
            flush_stdin()
            print(f"\n{Style.RESET_ALL}" + "-" * 50)

            if interrupted_text:
                next_user_text = interrupted_text

    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🔴 Apagando el robot... ¡Hasta la próxima! 👋{Style.RESET_ALL}")
        tts.speak("¡Hasta luego! Hiciste un gran trabajo hoy.")
    finally:
        # Restaurar terminal a su modo normal si se simuló teclado
        if old_term_settings:
            try:
                import termios
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_term_settings)
            except Exception:
                pass

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
