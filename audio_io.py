import time
import queue
import threading
import collections
import re
import numpy as np
import sounddevice as sd
from typing import Optional, List, Callable, Any
from config import SAMPLE_RATE, CHANNELS, SILENCE_DURATION, ENERGY_THRESHOLD, ENABLE_VOICE_INTERRUPT

WAKE_WORD_PATTERN = re.compile(r'\b(?:[hH]?elena+|elenita|lena|yalena|yelena|alena|olena)\b', re.IGNORECASE)

def has_wake_word(text: str) -> bool:
    """Verifica si el texto contiene 'Elena' o sus variantes fonéticas comunes"""
    if not text:
        return False
    return bool(WAKE_WORD_PATTERN.search(text))

def extract_message_after_wake_word(text: str) -> str:
    """Limpia la invocación de Elena si está al inicio o al final para procesar la consulta limpia"""
    if not text:
        return ""
    # Quitar del inicio
    cleaned = re.sub(r'^(?:hola\s+|oye\s+|hey\s+)?[hH]?elena+\b[\s,.:;-]*|\belenita\b[\s,.:;-]*', '', text, flags=re.IGNORECASE).strip()
    # Quitar del final si quedó al final (ej. "¿qué figuras hay, Elena?")
    cleaned = re.sub(r'[\s,.:;-]+(?:[hH]?elena+|elenita)\b[\s.!?]*$', '', cleaned, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else text.strip()

def is_stop_command(text: str) -> bool:
    """Verifica si la frase es una orden de parada, esté donde esté la palabra 'Elena'"""
    if not text:
        return False
    # Remover menciones a Elena para evaluar la orden central
    clean = re.sub(r'\b(?:[hH]?elena+|elenita|tobi)\b', '', text, flags=re.IGNORECASE)
    clean = re.sub(r'^[¿¡\s.!?]+|[¿¡\s.!?]+$', '', clean).lower().strip()
    clean = re.sub(r'\s+', ' ', clean).strip(' ,.:;-¿?¡!')
    words = clean.split()
    
    if len(words) > 3 or len(words) == 0:
        return False

    direct_stops = {
        "para", "alto", "stop", "detente", "cállate", "callate",
        "silencio", "pausa", "basta", "corta", "detener", "espera"
    }
    
    if clean in direct_stops:
        return True
        
    compound_stops = {
        "para ya", "alto ahí", "por favor para", "ya para", "haz una pausa"
    }
    if clean in compound_stops:
        return True

    return False

def is_exit_command(text: str) -> bool:
    """Verifica si la frase es una orden para salir o cerrar la conversación"""
    if not text:
        return False
    clean = re.sub(r'\b(?:[hH]?elena+|elenita|tobi)\b', '', text, flags=re.IGNORECASE)
    clean = re.sub(r'^[¿¡\s.!?]+|[¿¡\s.!?]+$', '', clean).lower().strip()
    clean = re.sub(r'\s+', ' ', clean).strip(' ,.:;-¿?¡!')
    words = clean.split()
    
    if len(words) > 4 or len(words) == 0:
        return False
    
    exit_words = {
        "salir", "exit", "adiós", "adios", "chao", "terminar",
        "cerrar", "apagar", "hasta luego", "nos vemos", "ya me voy"
    }
    if clean in exit_words or any(w in exit_words for w in words):
        return True
    return False

class AudioRecorder:
    """
    Manejador de Audio enfocado en conversación por turnos:
    - Turno del Robot: Reproducción fluida y continua sin cortes accidentales.
    - Interrupción selectiva: Solo se detiene si el usuario dice explícitamente 'para', 'alto', 'stop'.
    - Turno del Niño: Grabación con calibración de ruido ambiente y espera de silencio.
    """
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        silence_duration: float = SILENCE_DURATION,
        energy_threshold: float = ENERGY_THRESHOLD,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_duration = silence_duration
        self.energy_threshold = energy_threshold
        self.ambient_noise_level = min(0.015, max(0.003, self.energy_threshold * 0.8))

    def calibrate_ambient_noise(self, duration: float = 0.3):
        """Mide brevemente el ruido ambiente al inicio para calibrar el umbral dinámico"""
        try:
            samples = int(self.sample_rate * duration)
            rec = sd.rec(samples, samplerate=self.sample_rate, channels=self.channels, dtype="float32")
            sd.wait()
            rms = float(np.sqrt(np.mean(rec.flatten()**2)))
            if rms > 0:
                self.ambient_noise_level = min(0.035, max(0.002, rms))
                print(f" 🎚️ [Ruido ambiente calibrado: {self.ambient_noise_level:.4f} | Umbral inicio: {max(self.energy_threshold, self.ambient_noise_level * 1.55):.4f}]")
        except Exception:
            pass

    def _update_ambient_noise(self, energy: float):
        if energy > 0:
            # Adaptación suave al ruido ambiente real (ventiladores, USB, fondo)
            # Permite adaptarse a micrófonos ruidosos en Raspberry Pi sin bloquear voz real
            self.ambient_noise_level = min(0.035, 0.95 * self.ambient_noise_level + 0.05 * energy)

    def play_listening_beep(self, frequency: float = 680.0, duration: float = 0.09):
        """Genera y reproduce un tono 'pup' suave para indicar que el robot está listo para escuchar"""
        try:
            samples = int(self.sample_rate * duration)
            t = np.linspace(0, duration, samples, False)
            # Envolvente suave estilo campana (Hann) para que suene como un 'pup' limpio sin chasquido
            envelope = 0.5 * (1 - np.cos(2 * np.pi * t / duration))
            tone = np.sin(2 * np.pi * frequency * t) * envelope * 0.18
            sd.play(tone.astype(np.float32), self.sample_rate)
            sd.wait()
            time.sleep(0.05)  # Breve margen para que el parlante se apague por completo
        except Exception:
            pass

    def play_transcription_done_beep(self):
        """Genera un sonido agradable de confirmación de fin de transcripción (dos tonos sutiles ascendentes)"""
        try:
            duration = 0.06
            samples = int(self.sample_rate * duration)
            t = np.linspace(0, duration, samples, False)
            envelope = 0.5 * (1 - np.cos(2 * np.pi * t / duration))
            # Primer tono (880 Hz - La) seguido de segundo tono más agudo (1174 Hz - Re)
            tone1 = np.sin(2 * np.pi * 880.0 * t) * envelope * 0.15
            pause = np.zeros(int(self.sample_rate * 0.02), dtype=np.float32)
            tone2 = np.sin(2 * np.pi * 1174.0 * t) * envelope * 0.18
            chime = np.concatenate([tone1, pause, tone2]).astype(np.float32)
            sd.play(chime, self.sample_rate)
            sd.wait()
            time.sleep(0.05)
        except Exception:
            pass

    def is_speech(self, chunk: np.ndarray, is_already_speaking: bool = False) -> bool:
        """
        Detección estricta de voz nítida frente a ruidos/murmullos:
        - Inicio: requiere energía clara (>= 0.012 RMS) superior a murmullos y suspiros.
        - Sostenimiento: umbral firme para que murmullos o respiraciones no reseteen
          indebidamente el contador de silencio al finalizar el turno.
        """
        energy = float(np.sqrt(np.mean(chunk**2)))

        if is_already_speaking:
            # Sostenimiento de voz nítida (murmullos leves por debajo no reinician silencio)
            hold_threshold = max(self.ambient_noise_level * 1.5, self.energy_threshold * 1.0, 0.009)
            return energy > hold_threshold
        else:
            # Inicio: requiere voz nítida y audible (filtrando murmullos débiles)
            start_threshold = max(self.energy_threshold * 1.5, self.ambient_noise_level * 2.2, 0.012)
            if energy > start_threshold:
                return True
            else:
                self._update_ambient_noise(energy)
                return False

    def record_until_silence(
        self,
        initial_frames: Optional[List[np.ndarray]] = None,
        max_duration: float = 30.0,
        button_is_released_func: Optional[Callable[[], bool]] = None
    ) -> np.ndarray:
        """
        Escucha al niño durante su turno:
        - Si hay botón arcade: graba mientras esté presionado y corta al soltarlo.
        - Si es manos libres: requiere confirmación consecutiva de voz nítida
          y decide el contador final de silencio sin reiniciarse por murmullos.
        """
        chunk_duration = 0.05  # 50ms
        chunk_samples = int(self.sample_rate * chunk_duration)
        
        pre_buffer = collections.deque(maxlen=10)  # 500ms pre-buffer
        frames = list(initial_frames) if initial_frames else []
        is_speaking = bool(frames)
        silence_start_time = None
        start_time = time.time()
        record_start = start_time
        grace_period = 0.25

        consecutive_speech = 0
        min_consecutive_to_start = 3   # Requiere al menos ~150ms continuos de voz nítida
        speech_chunks_count = 0        # Cuenta de chunks de voz nítida real

        with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype="float32") as stream:
            # Descartar primeros 100ms de calentamiento del stream para purgar 'pops' de inicio de ALSA/USB
            try:
                for _ in range(2):
                    stream.read(chunk_samples)
            except Exception:
                pass

            while True:
                if (time.time() - start_time) > max_duration:
                    break

                audio_chunk, _ = stream.read(chunk_samples)
                audio_chunk = audio_chunk.flatten()

                # Si se configuró botón arcade / tecla: al soltarlo/pulsarlo se detiene la grabación en el acto
                elapsed = time.time() - record_start
                if button_is_released_func and elapsed >= grace_period and button_is_released_func():
                    print(" 🟢 [Grabación finalizada - Enviando tu voz a transcribir...]")
                    frames.append(audio_chunk)
                    is_speaking = True
                    break

                if button_is_released_func:
                    # En modo botón: se graba continuo sin límite de silencio
                    is_speaking = True
                    frames.append(audio_chunk)
                elif not is_speaking:
                    if self.is_speech(audio_chunk, is_already_speaking=False):
                        consecutive_speech += 1
                        pre_buffer.append(audio_chunk)
                        if consecutive_speech >= min_consecutive_to_start:
                            print(" 🎙️ [Voz detectada... te escucho]")
                            is_speaking = True
                            frames.extend(pre_buffer)
                            speech_chunks_count += consecutive_speech
                            silence_start_time = None
                    else:
                        consecutive_speech = 0
                        pre_buffer.append(audio_chunk)
                else:
                    if self.is_speech(audio_chunk, is_already_speaking=True):
                        speech_chunks_count += 1
                        frames.append(audio_chunk)
                        # Solo resetea el contador si habló con voz nítida sostenida
                        silence_start_time = None
                    else:
                        frames.append(audio_chunk)
                        # Respiraciones o murmullos leves no resetean el contador de silencio
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif (time.time() - silence_start_time) >= self.silence_duration:
                            break

        if not frames:
            return np.array([], dtype=np.float32)

        # En manos libres: si la voz detectada fue menor a ~250ms de voz nítida (5 chunks), descartar
        if not button_is_released_func and speech_chunks_count < 5:
            return np.array([], dtype=np.float32)

        full_audio = np.concatenate(frames)

        # Si se usó botón o push-to-talk, no recortamos por silence_duration
        if button_is_released_func:
            return full_audio

        # Filtro final de nitidez: verificar que el volumen pico corresponda a voz clara (>= 0.12)
        # Esto descarta murmullos, susurros débiles o chasquidos antes de enviarlos a transcribir
        peak_volume = float(np.max(np.abs(full_audio))) if len(full_audio) > 0 else 0.0
        if peak_volume < 0.12:
            return np.array([], dtype=np.float32)

        # En modo manos libres: recortar el exceso de silencio final dejando 0.35s de margen natural
        keep_silence = 0.35
        trim_seconds = max(0.0, self.silence_duration - keep_silence)
        trim_samples = int(self.sample_rate * trim_seconds)

        if len(full_audio) > (trim_samples + int(self.sample_rate * 0.5)):
            return full_audio[:-trim_samples]

        return full_audio

    def play_audio_queue(
        self,
        audio_queue: queue.Queue,
        stop_event: threading.Event,
        stt_transcribe_func: Optional[Callable[[np.ndarray], str]] = None,
        button_check_func: Optional[Callable[[], bool]] = None
    ) -> Optional[str]:
        """
        Reproduce fluidamente el turno del robot desde la cola precargada.
        - Se interrumpe al instante si se presiona el botón arcade físico (button_check_func).
        - O si el usuario dice 'Elena ...' / orden de parada ('para', 'alto').
        """
        chunk_duration = 0.05  # 50ms
        listener_stop = threading.Event()
        interrupted_user_text: Optional[str] = None

        def button_monitor():
            """Monitorea el botón físico arcade: al presionarlo corta la voz del robot al instante"""
            if not button_check_func:
                return
            # Período de gracia inicial (350ms) para evitar que teclas/rebotes del final de la grabación
            # corten el arranque de la voz de Elena.
            time.sleep(0.35)
            while not stop_event.is_set() and not listener_stop.is_set():
                if button_check_func():
                    print(f"\n 🛑 [¡Botón presionado! Cortando la voz del robot inmediatamente...]")
                    stop_event.set()
                    while not audio_queue.empty():
                        try:
                            audio_queue.get_nowait()
                        except queue.Empty:
                            break
                    break
                time.sleep(0.04)

        def stop_word_listener():
            """Monitorea el micrófono en segundo plano para permitir interrupción cuando el usuario hable con voz nítida"""
            nonlocal interrupted_user_text
            if not stt_transcribe_func:
                return

            chunk_samples = int(self.sample_rate * chunk_duration)
            # Para interrumpir por encima del parlante, requiere energía clara y firme
            high_threshold = max(0.040, self.ambient_noise_level * 5.0)

            try:
                with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype="float32") as in_stream:
                    try:
                        for _ in range(2):
                            in_stream.read(chunk_samples)
                    except Exception:
                        pass

                    consecutive_high = 0
                    while not stop_event.is_set() and not listener_stop.is_set():
                        mic_chunk, _ = in_stream.read(chunk_samples)
                        mic_chunk = mic_chunk.flatten()
                        energy = float(np.sqrt(np.mean(mic_chunk**2)))

                        # Si alguien habla con energía nítida por encima del parlante (no murmullos)
                        if energy > high_threshold:
                            consecutive_high += 1
                            if consecutive_high >= 2:  # Al menos 100ms sostenidos para no cortar por clics
                                captured = [mic_chunk]
                                silence_count = 0
                                # Capturar hasta 3.5 segundos de la frase de interrupción
                                for _ in range(70):
                                    if stop_event.is_set() or listener_stop.is_set():
                                        break
                                    next_c, _ = in_stream.read(chunk_samples)
                                    next_c = next_c.flatten()
                                    captured.append(next_c)
                                    chk_e = float(np.sqrt(np.mean(next_c**2)))
                                    if chk_e < high_threshold * 0.75:
                                        silence_count += 1
                                        if silence_count >= 8:  # 400ms de silencio tras la frase
                                            break
                                    else:
                                        silence_count = 0

                                consecutive_high = 0
                                if len(captured) >= 7:  # Al menos 350ms de audio capturado
                                    audio_arr = np.concatenate(captured)
                                    peak_val = float(np.max(np.abs(audio_arr)))
                                    # Exigir volumen pico nítido (>= 0.14) para descartar murmullos o ruidos del parlante
                                    if peak_val >= 0.14:
                                        try:
                                            transcription = stt_transcribe_func(audio_arr)
                                            if transcription and len(transcription.strip()) >= 2:
                                                clean_text = extract_message_after_wake_word(transcription)
                                                final_text = clean_text if clean_text else transcription.strip()
                                                print(f"\n 🛑 [¡Interrupción por voz detectada: \"{final_text}\"! Deteniendo al robot...]")
                                                interrupted_user_text = final_text
                                                stop_event.set()
                                                # Vaciar la cola para detener la reproducción de inmediato
                                                while not audio_queue.empty():
                                                    try:
                                                        audio_queue.get_nowait()
                                                    except queue.Empty:
                                                        break
                                                break
                                        except Exception:
                                            pass
                        else:
                            consecutive_high = 0
            except Exception:
                # Si el hardware de audio no permite dúplex simultáneo, continúa en modo por turnos
                pass

        # Iniciar hilo de corte por botón físico si está disponible
        button_thread = None
        if button_check_func:
            button_thread = threading.Thread(target=button_monitor, daemon=True)
            button_thread.start()

        # Iniciar hilo de escucha exclusivo para la palabra 'Elena' o 'para'
        listener_thread = None
        if ENABLE_VOICE_INTERRUPT and stt_transcribe_func:
            listener_thread = threading.Thread(target=stop_word_listener, daemon=True)
            listener_thread.start()

        try:
            while not stop_event.is_set():
                try:
                    # Esperar hasta 20s para la siguiente frase del modelo
                    item = audio_queue.get(timeout=20.0)
                except queue.Empty:
                    break

                if item is None:
                    break

                audio_data, sample_rate = item
                if audio_data is None or len(audio_data) == 0:
                    continue

                out_channels = 1 if audio_data.ndim == 1 else audio_data.shape[1]
                out_chunk_size = int(sample_rate * chunk_duration)
                total_samples = len(audio_data)
                current_pos = 0

                with sd.OutputStream(samplerate=sample_rate, channels=out_channels, dtype="float32") as out_stream:
                    while current_pos < total_samples and not stop_event.is_set():
                        next_pos = min(current_pos + out_chunk_size, total_samples)
                        chunk_to_play = audio_data[current_pos:next_pos]

                        if len(chunk_to_play) < out_chunk_size:
                            if out_channels == 1:
                                chunk_to_play = np.pad(chunk_to_play, (0, out_chunk_size - len(chunk_to_play)))
                            else:
                                chunk_to_play = np.pad(chunk_to_play, ((0, out_chunk_size - len(chunk_to_play)), (0, 0)))

                        out_stream.write(chunk_to_play.astype(np.float32))
                        current_pos = next_pos

        finally:
            listener_stop.set()
            if listener_thread and listener_thread.is_alive():
                listener_thread.join(timeout=0.2)

        return interrupted_user_text

