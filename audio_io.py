import time
import queue
import threading
import collections
import numpy as np
import sounddevice as sd
from typing import Optional, List
from config import SAMPLE_RATE, CHANNELS, SILENCE_DURATION

class AudioRecorder:
    """
    Manejador de Audio con:
    - Pre-buffer rodante para no perder inicios de frase.
    - Calibración continua del piso de ruido.
    - Reproducción continua sin pausas entre oraciones.
    - Detección de interrupciones (Barge-in).
    """
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        silence_duration: float = SILENCE_DURATION,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_duration = silence_duration
        self.ambient_noise_level = 0.005

    def _update_ambient_noise(self, energy: float):
        if energy > 0:
            self.ambient_noise_level = 0.95 * self.ambient_noise_level + 0.05 * energy

    def is_speech(self, chunk: np.ndarray) -> bool:
        energy = float(np.sqrt(np.mean(chunk**2)))
        dynamic_threshold = max(0.006, self.ambient_noise_level * 2.2)

        if energy > dynamic_threshold:
            return True
        else:
            self._update_ambient_noise(energy)
            return False

    def record_until_silence(
        self,
        initial_frames: Optional[List[np.ndarray]] = None,
        max_duration: float = 30.0
    ) -> np.ndarray:
        chunk_duration = 0.05  # 50ms
        chunk_samples = int(self.sample_rate * chunk_duration)
        
        pre_buffer = collections.deque(maxlen=7)
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

                if self.is_speech(audio_chunk):
                    if not is_speaking:
                        print(" 🎙️ [Voz detectada... escuchando]")
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

        return np.concatenate(frames)

    def play_audio_queue(
        self,
        audio_queue: queue.Queue,
        stop_event: threading.Event
    ) -> Optional[np.ndarray]:
        """
        Reproduce fluidamente elementos de audio desde la cola precargada.
        """
        chunk_duration = 0.05  # 50ms
        in_chunk_size = int(self.sample_rate * chunk_duration)
        
        consecutive_voice_chunks = 0
        captured_frames = []
        is_interrupted = False

        with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype="float32") as in_stream:
            while not stop_event.is_set():
                try:
                    # Esperar hasta 20s para dar tiempo a que la primera frase se descargue
                    item = audio_queue.get(timeout=20.0)
                except queue.Empty:
                    break

                # Señal de fin de todas las oraciones
                if item is None:
                    break

                audio_data, sample_rate = item
                if audio_data is None or len(audio_data) == 0:
                    continue

                out_channels = 1 if audio_data.ndim == 1 else audio_data.shape[1]
                out_chunk_size = int(sample_rate * chunk_duration)
                total_samples = len(audio_data)
                current_pos = 0
                chunk_index = 0

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
                        chunk_index += 1

                        # Monitorear micrófono
                        mic_chunk, _ = in_stream.read(in_chunk_size)
                        mic_chunk = mic_chunk.flatten()
                        energy = float(np.sqrt(np.mean(mic_chunk**2)))

                        # Umbral de interrupción (ignorar los primeros 100ms de inicio de parlante)
                        interrupt_threshold = max(0.015, self.ambient_noise_level * 3.0)

                        if chunk_index > 2 and energy > interrupt_threshold:
                            consecutive_voice_chunks += 1
                            captured_frames.append(mic_chunk)
                            if consecutive_voice_chunks >= 3:  # ~150ms continuos de voz humana
                                print("\n 🛑 [¡Interrupción! El niño habló, cortando voz...]")
                                is_interrupted = True
                                stop_event.set()
                                # Vaciar cola restante
                                while not audio_queue.empty():
                                    try:
                                        audio_queue.get_nowait()
                                    except queue.Empty:
                                        break
                                break
                        else:
                            consecutive_voice_chunks = 0
                            if not is_interrupted:
                                captured_frames.clear()

                if is_interrupted:
                    break

        if is_interrupted:
            return self.record_until_silence(initial_frames=captured_frames)

        return None
