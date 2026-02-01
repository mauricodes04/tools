"""
Audio recording module using sounddevice.
Provides threaded recording with chunk-based callbacks for real-time processing.
"""

import queue
import threading
import wave
import tempfile
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime

import numpy as np
import sounddevice as sd

from ..utils.paths import get_temp_dir
from ..utils.config import get_config


class AudioRecorder:
    """
    Records audio from the microphone with real-time chunk callbacks.
    
    Provides audio chunks to a callback function for real-time transcription
    while simultaneously saving the complete recording for final processing.
    """
    
    def __init__(
        self,
        chunk_callback: Optional[Callable[[np.ndarray], None]] = None,
        chunk_duration: float = 1.5,
        overlap_duration: float = 0.5
    ):
        """
        Initialize the audio recorder.
        
        Args:
            chunk_callback: Function called with audio chunks for real-time processing
            chunk_duration: Duration of each chunk in seconds
            overlap_duration: Overlap between chunks in seconds
        """
        self.config = get_config()
        self.sample_rate = self.config.sample_rate
        self.channels = 1  # Mono for speech recognition
        
        self.chunk_callback = chunk_callback
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        
        # Calculate chunk sizes in samples
        self.chunk_samples = int(self.chunk_duration * self.sample_rate)
        self.overlap_samples = int(self.overlap_duration * self.sample_rate)
        
        # Recording state
        self.is_recording = False
        self.audio_queue: queue.Queue = queue.Queue()
        self.recorded_audio: list = []
        self.audio_buffer: np.ndarray = np.array([], dtype=np.float32)
        
        # Threading
        self._stream: Optional[sd.InputStream] = None
        self._recording_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Temp file for saving recording
        self._temp_file: Optional[Path] = None
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Callback for sounddevice InputStream."""
        if status:
            print(f"Audio callback status: {status}")
        
        # Add audio data to queue for processing
        self.audio_queue.put(indata.copy())
    
    def _process_audio_chunks(self):
        """Process audio chunks in a separate thread."""
        while not self._stop_event.is_set() or not self.audio_queue.empty():
            try:
                # Get audio data from queue with timeout
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # Flatten and store for final recording
                flat_audio = audio_data.flatten()
                self.recorded_audio.append(flat_audio)
                
                # Add to buffer for chunk processing
                self.audio_buffer = np.concatenate([self.audio_buffer, flat_audio])
                
                # If we have enough data, send a chunk to callback
                if len(self.audio_buffer) >= self.chunk_samples and self.chunk_callback:
                    chunk = self.audio_buffer[:self.chunk_samples].copy()
                    
                    # Keep overlap for context continuity
                    self.audio_buffer = self.audio_buffer[self.chunk_samples - self.overlap_samples:]
                    
                    # Call the callback with the chunk
                    try:
                        self.chunk_callback(chunk)
                    except Exception as e:
                        print(f"Chunk callback error: {e}")
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Audio processing error: {e}")
    
    def start_recording(self) -> bool:
        """
        Start recording audio from the microphone.
        
        Returns:
            True if recording started successfully, False otherwise.
        """
        if self.is_recording:
            return False
        
        try:
            # Reset state
            self.recorded_audio = []
            self.audio_buffer = np.array([], dtype=np.float32)
            self.audio_queue = queue.Queue()
            self._stop_event.clear()
            
            # Create input stream
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                callback=self._audio_callback,
                blocksize=int(self.sample_rate * 0.1)  # 100ms blocks
            )
            
            # Start processing thread
            self._recording_thread = threading.Thread(
                target=self._process_audio_chunks,
                daemon=True
            )
            self._recording_thread.start()
            
            # Start the stream
            self._stream.start()
            self.is_recording = True
            
            return True
            
        except Exception as e:
            print(f"Failed to start recording: {e}")
            self.is_recording = False
            return False
    
    def stop_recording(self) -> Optional[Path]:
        """
        Stop recording and save the audio to a temporary WAV file.
        
        Returns:
            Path to the saved WAV file, or None if failed.
        """
        if not self.is_recording:
            return None
        
        try:
            # Stop the stream
            self._stream.stop()
            self._stream.close()
            
            # Signal processing thread to stop
            self._stop_event.set()
            if self._recording_thread:
                self._recording_thread.join(timeout=2.0)
            
            self.is_recording = False
            
            # Combine all recorded audio
            if not self.recorded_audio:
                return None
            
            full_audio = np.concatenate(self.recorded_audio)
            
            # Save to temporary WAV file
            self._temp_file = self._save_wav(full_audio)
            
            return self._temp_file
            
        except Exception as e:
            print(f"Failed to stop recording: {e}")
            self.is_recording = False
            return None
    
    def _save_wav(self, audio_data: np.ndarray) -> Path:
        """Save audio data to a WAV file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = get_temp_dir() / f"recording_{timestamp}.wav"
        
        # Convert float32 [-1, 1] to int16
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        with wave.open(str(temp_file), 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
        
        return temp_file
    
    def get_recording_duration(self) -> float:
        """Get the current recording duration in seconds."""
        if not self.recorded_audio:
            return 0.0
        
        total_samples = sum(len(chunk) for chunk in self.recorded_audio)
        return total_samples / self.sample_rate
    
    def get_full_audio(self) -> Optional[np.ndarray]:
        """Get the complete recorded audio as a numpy array."""
        if not self.recorded_audio:
            return None
        return np.concatenate(self.recorded_audio)
    
    @staticmethod
    def get_input_devices() -> list:
        """Get list of available input devices."""
        devices = sd.query_devices()
        input_devices = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })
        return input_devices
    
    @staticmethod
    def get_default_input_device() -> Optional[dict]:
        """Get the default input device info."""
        try:
            device_id = sd.default.device[0]
            if device_id is not None:
                device = sd.query_devices(device_id)
                return {
                    'index': device_id,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                }
        except Exception:
            pass
        return None
