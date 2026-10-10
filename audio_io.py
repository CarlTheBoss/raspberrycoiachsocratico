import time
import queue
import threading
import collections
import re
import numpy as np
import sounddevice as sd
from typing import Optional, List, Callable, Any
from config import SAMPLE_RATE, CHANNELS, SILENCE_DURATION, ENERGY_THRESHOLD

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
        self.ambient_noise_level = 0.005

    def _update_ambient_noise(self, energy: float):
        if energy > 0:
            # Limitar el nivel de ruido base para que nunca bloquee susurros o voz baja
            self.ambient_noise_level = min(0.004, 0.95 * self.ambient_noise_level + 0.05 * energy)

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
        except Exception:
            pass

    def is_speech(self, chunk: np.ndarray, is_already_speaking: bool = False) -> bool:
        """
        Detección de voz por histéresis ultrasensible a susurros y voz baja:
        - Detecta el inicio de voz con energía baja (0.0035).
        - Si ya está hablando, mantiene la escucha activa con umbral mínimo (0.002) para capturar
          susurros continuos, titubeos ('ammm', 'emmm') y pausas vocales.
        """
        energy = float(np.sqrt(np.mean(chunk**2)))

        if is_already_speaking:
            # Umbral de sostenimiento ultra sensible para susurros
            hold_threshold = max(0.002, self.energy_threshold * 0.45)
            return energy > hold_threshold
        else:
            # Umbral de inicio para activar el turno con voz baja
            start_threshold = max(self.energy_threshold, self.ambient_noise_level * 1.2)
            if energy > start_threshold:
                return True
            else:
                self._update_ambient_noise(energy)
                return False

    def record_until_silence(
        self,
        initial_frames: Optional[List[np.ndarray]] = None,
        max_duration: float = 30.0
    ) -> np.ndarray:
        """
        Escucha al niño durante su turno. Permite pausas naturales de pensamiento
        y murmullos ('ammm', 'emmm') sin cortar antes de tiempo.
        """
        chunk_duration = 0.05  # 50ms
        chunk_samples = int(self.sample_rate * chunk_duration)
        
        pre_buffer = collections.deque(maxlen=10)  # 500ms pre-buffer
        frames = list(initial_frames) if initial_frames else []
        is_speaking = bool(frames)
        silence_start_time = None
        start_time = time.time()

        with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype="float32") as stream:
            while True:
                if (time.time() - start_time) > max_duration:
                    break

                audio_chunk, _ = stream.read(chunk_samples)
                audio_chunk = audio_chunk.flatten()

                if self.is_speech(audio_chunk, is_already_speaking=is_speaking):
                    if not is_speaking:
                        print(" 🎙️ [Voz detectada... te escucho]")
                        is_speaking = True
                        frames.extend(pre_buffer)
                    frames.append(audio_chunk)
                    silence_start_time = None
                else:
                    if is_speaking:
                        frames.append(audio_chunk)
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif (time.time() - silence_start_time) >= self.silence_duration:
                            break
                    else:
                        pre_buffer.append(audio_chunk)

        if not frames or not is_speaking:
            return np.array([], dtype=np.float32)

        full_audio = np.concatenate(frames)

        # Recortar el exceso de silencio final dejando 0.35s de margen natural
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
        stt_transcribe_func: Optional[Callable[[np.ndarray], str]] = None
    ) -> Optional[str]:
        """
        Reproduce fluidamente el turno del robot desde la cola precargada.
        - Solo se interrumpe si el usuario dice 'Elena ...' o una orden de detención ('para', 'alto').
        - Retorna el texto del usuario si interrumpió diciendo 'Elena ...', o None si completó su turno.
        """
        chunk_duration = 0.05  # 50ms
        listener_stop = threading.Event()
        interrupted_user_text: Optional[str] = None

        def stop_word_listener():
            """Monitorea el micrófono en segundo plano buscando ÚNICAMENTE 'Elena' o 'Para'"""
            nonlocal interrupted_user_text
            if not stt_transcribe_func:
                return

            chunk_samples = int(self.sample_rate * chunk_duration)
            high_threshold = max(0.035, self.ambient_noise_level * 4.5)

            try:
                with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype="float32") as in_stream:
                    while not stop_event.is_set() and not listener_stop.is_set():
                        mic_chunk, _ = in_stream.read(chunk_samples)
                        mic_chunk = mic_chunk.flatten()
                        energy = float(np.sqrt(np.mean(mic_chunk**2)))

                        # Si alguien habla con energía suficiente por encima del parlante
                        if energy > high_threshold:
                            captured = [mic_chunk]
                            silence_count = 0
                            # Capturar hasta 3 segundos para permitir 'Elena, [lo que le digo]'
                            for _ in range(60):
                                if stop_event.is_set() or listener_stop.is_set():
                                    break
                                next_c, _ = in_stream.read(chunk_samples)
                                next_c = next_c.flatten()
                                captured.append(next_c)
                                chk_e = float(np.sqrt(np.mean(next_c**2)))
                                if chk_e < high_threshold:
                                    silence_count += 1
                                    if silence_count >= 8:  # 400ms de silencio tras la frase
                                        break
                                else:
                                    silence_count = 0

                            if len(captured) >= 6:  # Al menos 300ms de voz
                                audio_arr = np.concatenate(captured)
                                try:
                                    transcription = stt_transcribe_func(audio_arr)
                                    if transcription:
                                        # Interrumpir si mencionó 'Elena' o una orden de parada ('para', 'stop')
                                        if has_wake_word(transcription) or is_stop_command(transcription):
                                            print(f"\n 🛑 [¡Llamaste a Elena: '{transcription}'! Interrumpiendo voz...]")
                                            interrupted_user_text = transcription
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
            except Exception:
                # Si el hardware de audio no permite dúplex simultáneo, continúa en modo por turnos
                pass

        # Iniciar hilo de escucha exclusivo para la palabra 'Elena' o 'para'
        listener_thread = None
        if stt_transcribe_func:
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

