"""
Ambient listening module for Duet LLM.

Captures audio from microphone, detects speech using VAD,
transcribes with Whisper, and extracts topics for the room persona.
"""

import queue
import threading
import time
from collections import deque

import numpy as np

# Optional imports - checked at runtime
try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class AmbientListener:
    """
    Listens to ambient audio, transcribes speech, and queues topics.

    Usage:
        listener = AmbientListener()
        listener.start()

        # In your main loop:
        topic = listener.get_topic()  # Returns None if no new topics

        listener.stop()
    """

    def __init__(
        self,
        whisper_model: str = "base",
        sample_rate: int = 16000,
        chunk_duration: float = 0.5,
        silence_threshold: float = 0.01,
        speech_min_duration: float = 1.0,
        speech_max_duration: float = 10.0,
        cooldown: float = 2.0,
    ):
        """
        Initialize the ambient listener.

        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large)
            sample_rate: Audio sample rate in Hz
            chunk_duration: Duration of each audio chunk in seconds
            silence_threshold: RMS threshold below which audio is considered silence
            speech_min_duration: Minimum speech duration to transcribe (seconds)
            speech_max_duration: Maximum speech duration before forced transcription
            cooldown: Seconds to wait after transcription before listening again
        """
        if not HAS_SOUNDDEVICE:
            raise RuntimeError("sounddevice not installed. Run: pip install sounddevice")
        if not HAS_WHISPER:
            raise RuntimeError("faster-whisper not installed. Run: pip install faster-whisper")

        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)
        self.silence_threshold = silence_threshold
        self.speech_min_duration = speech_min_duration
        self.speech_max_duration = speech_max_duration
        self.cooldown = cooldown

        # Load Whisper model
        print(f"Loading Whisper model '{whisper_model}'...")
        device = "cpu"
        compute_type = "int8"

        # Use GPU if available on Apple Silicon
        if HAS_TORCH and torch.backends.mps.is_available():
            # faster-whisper doesn't support MPS yet, stick with CPU
            pass

        self.whisper = WhisperModel(whisper_model, device=device, compute_type=compute_type)
        print("Whisper model loaded.")

        # Topic queue (main thread consumes this)
        self.topic_queue = queue.Queue()

        # Recent transcriptions (for deduplication)
        self.recent_transcriptions = deque(maxlen=10)

        # Threading
        self._running = False
        self._thread = None

        # Audio state
        self._audio_buffer = []
        self._is_speaking = False
        self._speech_start_time = None

    def start(self):
        """Start listening in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("Ambient listener started.")

    def stop(self):
        """Stop listening."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("Ambient listener stopped.")

    def get_topic(self) -> str | None:
        """
        Get the next topic from the queue.
        Returns None if no topics available.
        """
        try:
            return self.topic_queue.get_nowait()
        except queue.Empty:
            return None

    def _listen_loop(self):
        """Main listening loop (runs in background thread)."""

        def audio_callback(indata, frames, time_info, status):
            """Called for each audio chunk."""
            if status:
                print(f"Audio status: {status}")

            # Calculate RMS (volume level)
            audio = indata[:, 0]  # Mono
            rms = np.sqrt(np.mean(audio ** 2))

            is_speech = rms > self.silence_threshold

            if is_speech:
                if not self._is_speaking:
                    # Speech started
                    self._is_speaking = True
                    self._speech_start_time = time.time()
                    self._audio_buffer = []

                self._audio_buffer.append(audio.copy())

                # Check if we've hit max duration
                duration = time.time() - self._speech_start_time
                if duration >= self.speech_max_duration:
                    self._process_speech()
            else:
                if self._is_speaking:
                    # Speech ended
                    duration = time.time() - self._speech_start_time
                    if duration >= self.speech_min_duration:
                        self._process_speech()
                    else:
                        # Too short, discard
                        self._audio_buffer = []

                    self._is_speaking = False
                    self._speech_start_time = None

        # Start audio stream
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32,
            blocksize=self.chunk_size,
            callback=audio_callback,
        ):
            while self._running:
                time.sleep(0.1)

    def _process_speech(self):
        """Transcribe buffered audio and extract topics."""
        if not self._audio_buffer:
            return

        # Concatenate audio chunks
        audio = np.concatenate(self._audio_buffer)
        self._audio_buffer = []

        # Transcribe with Whisper
        try:
            segments, info = self.whisper.transcribe(
                audio,
                language="en",
                vad_filter=True,  # Use Whisper's built-in VAD too
            )

            text = " ".join(segment.text for segment in segments).strip()

            if text and len(text) > 10:  # Filter very short transcriptions
                # Check for duplicates
                if text.lower() not in [t.lower() for t in self.recent_transcriptions]:
                    self.recent_transcriptions.append(text)

                    # Extract topic (for now, just use the transcription)
                    # Could add keyword extraction here later
                    topic = self._extract_topic(text)

                    if topic:
                        print(f"[Listener] Heard: {topic}")
                        self.topic_queue.put(topic)

                        # Cooldown
                        time.sleep(self.cooldown)

        except Exception as e:
            print(f"[Listener] Transcription error: {e}")

    def _extract_topic(self, text: str) -> str | None:
        """
        Extract a topic from transcribed text.

        For now, just cleans up and returns the text.
        Could be enhanced with keyword extraction or LLM summarization.
        """
        # Basic cleanup
        text = text.strip()

        # Filter out common filler/noise
        noise_phrases = [
            "thank you",
            "okay",
            "um",
            "uh",
            "hmm",
            "yeah",
            "so",
        ]

        lower = text.lower()
        for phrase in noise_phrases:
            if lower == phrase:
                return None

        return text


def check_dependencies():
    """Check if all required dependencies are installed."""
    missing = []

    if not HAS_SOUNDDEVICE:
        missing.append("sounddevice")
    if not HAS_WHISPER:
        missing.append("faster-whisper")

    if missing:
        print("Missing dependencies for ambient listening:")
        print(f"  pip install {' '.join(missing)}")
        return False

    return True


if __name__ == "__main__":
    # Test the listener
    if not check_dependencies():
        exit(1)

    print("Testing ambient listener...")
    print("Speak into your microphone. Press Ctrl+C to stop.\n")

    listener = AmbientListener(whisper_model="base")
    listener.start()

    try:
        while True:
            topic = listener.get_topic()
            if topic:
                print(f"\n>>> Topic detected: {topic}\n")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        listener.stop()
