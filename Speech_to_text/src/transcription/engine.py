"""
Transcription engine using faster-whisper for speech-to-text conversion.
Supports real-time chunk processing and final full-audio transcription.
"""

import os
import threading
from pathlib import Path
from typing import Callable, Optional, Generator, Tuple
from dataclasses import dataclass

import numpy as np

from ..utils.paths import get_models_dir
from ..utils.config import get_config


@dataclass
class TranscriptionSegment:
    """Represents a transcribed segment with optional timestamps."""
    text: str
    start: float  # Start time in seconds
    end: float    # End time in seconds
    
    def format_timestamp(self) -> str:
        """Format the start timestamp as [HH:MM:SS]."""
        hours = int(self.start // 3600)
        minutes = int((self.start % 3600) // 60)
        seconds = int(self.start % 60)
        return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"


class TranscriptionEngine:
    """
    Speech-to-text engine using faster-whisper.
    
    Provides both real-time chunk processing for preview and
    final full-audio transcription for accurate output.
    """
    
    LANGUAGE_CODES = {
        "English": "en",
        "Spanish": "es",
    }
    
    def __init__(self):
        """Initialize the transcription engine."""
        self.config = get_config()
        self._model = None
        self._model_lock = threading.Lock()
        self._is_loading = False
        self._load_error: Optional[str] = None
        
    def _get_model_path(self) -> Path:
        """Get the path to the Whisper model."""
        models_dir = get_models_dir()
        model_size = self.config.model_size
        return models_dir / f"whisper-{model_size}"
    
    def is_model_loaded(self) -> bool:
        """Check if the model is currently loaded."""
        return self._model is not None
    
    def is_loading(self) -> bool:
        """Check if the model is currently being loaded."""
        return self._is_loading
    
    def get_load_error(self) -> Optional[str]:
        """Get the last model loading error, if any."""
        return self._load_error
    
    def load_model(
        self,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Load the Whisper model.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if model loaded successfully, False otherwise.
        """
        if self._model is not None:
            return True
        
        with self._model_lock:
            if self._model is not None:
                return True
            
            self._is_loading = True
            self._load_error = None
            
            try:
                if progress_callback:
                    progress_callback("Loading speech recognition model...")
                
                from faster_whisper import WhisperModel
                
                model_size = self.config.model_size
                compute_type = self.config.compute_type
                models_dir = get_models_dir()
                
                if progress_callback:
                    progress_callback(f"Loading {model_size} model (this may take a moment)...")
                
                # Determine optimal CPU thread count
                cpu_threads = self.config.cpu_threads
                if cpu_threads <= 0:
                    # Auto-detect: use all available CPU cores
                    cpu_threads = os.cpu_count() or 4
                
                num_workers = self.config.num_workers
                if num_workers <= 0:
                    num_workers = 1
                
                if progress_callback:
                    progress_callback(f"Using {cpu_threads} CPU threads...")
                
                # Load the model with optimized settings
                self._model = WhisperModel(
                    model_size,
                    device="cpu",
                    compute_type=compute_type,
                    download_root=str(models_dir),
                    cpu_threads=cpu_threads,
                    num_workers=num_workers
                )
                
                if progress_callback:
                    progress_callback("Model loaded successfully!")
                
                return True
                
            except Exception as e:
                self._load_error = str(e)
                if progress_callback:
                    progress_callback(f"Failed to load model: {e}")
                return False
                
            finally:
                self._is_loading = False
    
    def transcribe_chunk(
        self,
        audio_chunk: np.ndarray,
        language: str = "English"
    ) -> str:
        """
        Transcribe a short audio chunk for real-time preview.
        
        Args:
            audio_chunk: Audio data as numpy array (float32, 16kHz)
            language: Language name ("English" or "Spanish")
            
        Returns:
            Transcribed text from the chunk.
        """
        if self._model is None:
            return ""
        
        try:
            lang_code = self.LANGUAGE_CODES.get(language, "en")
            
            # Transcribe with minimal beam size for speed
            segments, _ = self._model.transcribe(
                audio_chunk,
                language=lang_code,
                beam_size=1,  # Faster for real-time
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                ),
            )
            
            # Collect all segment texts
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
            
            return " ".join(text_parts)
            
        except Exception as e:
            print(f"Chunk transcription error: {e}")
            return ""
    
    def transcribe_file(
        self,
        audio_path: Path,
        language: str = "English",
        include_timestamps: bool = False,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Generator[TranscriptionSegment, None, None]:
        """
        Transcribe an audio file with full accuracy.
        
        Args:
            audio_path: Path to the audio file
            language: Language name ("English" or "Spanish")
            include_timestamps: Whether to include word timestamps
            progress_callback: Callback with (progress_fraction, current_text)
            
        Yields:
            TranscriptionSegment objects with text and timing.
        """
        if self._model is None:
            if not self.load_model():
                return
        
        try:
            lang_code = self.LANGUAGE_CODES.get(language, "en")
            
            # Full transcription with higher accuracy settings
            segments, info = self._model.transcribe(
                str(audio_path),
                language=lang_code,
                beam_size=5,
                vad_filter=True,
                word_timestamps=include_timestamps,
            )
            
            total_duration = info.duration if info.duration else 1.0
            
            for segment in segments:
                # Calculate progress
                progress = min(segment.end / total_duration, 1.0)
                
                result = TranscriptionSegment(
                    text=segment.text.strip(),
                    start=segment.start,
                    end=segment.end
                )
                
                if progress_callback:
                    progress_callback(progress, result.text)
                
                yield result
                
        except Exception as e:
            print(f"File transcription error: {e}")
            raise
    
    def transcribe_audio(
        self,
        audio_data: np.ndarray,
        language: str = "English",
        include_timestamps: bool = False,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Generator[TranscriptionSegment, None, None]:
        """
        Transcribe audio data (numpy array) with full accuracy.
        
        Args:
            audio_data: Audio as numpy array (float32, 16kHz mono)
            language: Language name ("English" or "Spanish")
            include_timestamps: Whether to include timestamps
            progress_callback: Callback with (progress_fraction, current_text)
            
        Yields:
            TranscriptionSegment objects with text and timing.
        """
        if self._model is None:
            if not self.load_model():
                return
        
        try:
            lang_code = self.LANGUAGE_CODES.get(language, "en")
            
            segments, info = self._model.transcribe(
                audio_data,
                language=lang_code,
                beam_size=5,
                vad_filter=True,
                word_timestamps=include_timestamps,
            )
            
            # Estimate duration from audio length
            sample_rate = 16000
            total_duration = len(audio_data) / sample_rate
            
            for segment in segments:
                progress = min(segment.end / total_duration, 1.0) if total_duration > 0 else 1.0
                
                result = TranscriptionSegment(
                    text=segment.text.strip(),
                    start=segment.start,
                    end=segment.end
                )
                
                if progress_callback:
                    progress_callback(progress, result.text)
                
                yield result
                
        except Exception as e:
            print(f"Audio transcription error: {e}")
            raise
    
    def format_transcription(
        self,
        segments: list[TranscriptionSegment],
        include_timestamps: bool = False
    ) -> str:
        """
        Format transcription segments into final text.
        
        Args:
            segments: List of TranscriptionSegment objects
            include_timestamps: Whether to include [HH:MM:SS] markers
            
        Returns:
            Formatted transcription text.
        """
        lines = []
        
        for segment in segments:
            if include_timestamps:
                lines.append(f"{segment.format_timestamp()} {segment.text}")
            else:
                lines.append(segment.text)
        
        # Join with appropriate spacing
        if include_timestamps:
            return "\n".join(lines)
        else:
            return " ".join(lines)
    
    def unload_model(self):
        """Unload the model to free memory."""
        with self._model_lock:
            self._model = None


# Global engine instance
_engine: Optional[TranscriptionEngine] = None


def get_engine() -> TranscriptionEngine:
    """Get the global transcription engine instance."""
    global _engine
    if _engine is None:
        _engine = TranscriptionEngine()
    return _engine
