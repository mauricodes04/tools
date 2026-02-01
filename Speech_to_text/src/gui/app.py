"""
Main application window for Speech-to-Text.
"""

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, List

import customtkinter as ctk

from .widgets import (
    TranscriptionPreview,
    RecordingIndicator,
    ProgressFrame,
    LanguageSelector,
    TimestampToggle
)
from ..audio.recorder import AudioRecorder
from ..audio.converter import (
    prepare_file_for_transcription,
    get_file_dialog_filetypes,
    is_video_file
)
from ..transcription.engine import get_engine, TranscriptionSegment
from ..utils.config import get_config
from ..utils.paths import clean_temp_files


class SpeechToTextApp(ctk.CTk):
    """Main application window."""
    
    WINDOW_TITLE = "Speech to Text"
    WINDOW_SIZE = (800, 600)
    MIN_SIZE = (600, 400)
    
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title(self.WINDOW_TITLE)
        self.geometry(f"{self.WINDOW_SIZE[0]}x{self.WINDOW_SIZE[1]}")
        self.minsize(*self.MIN_SIZE)
        
        # Set appearance
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        
        # Get config and engine
        self.config = get_config()
        self.engine = get_engine()
        
        # State
        self._is_recording = False
        self._is_processing = False
        self._current_audio_path: Optional[Path] = None
        self._transcription_segments: list[TranscriptionSegment] = []
        self._recorder: Optional[AudioRecorder] = None
        self._duration_update_job: Optional[str] = None
        
        # Batch processing state
        self._batch_files: List[Path] = []
        self._current_file_index: int = 0
        self._batch_transcriptions: dict[str, str] = {}  # filename -> transcription
        self._batch_output_dir: Optional[Path] = None  # Output directory for batch
        self._temp_audio_files: List[Path] = []  # Track temp files for cleanup
        
        # Build UI
        self._create_widgets()
        self._create_layout()
        self._bind_events()
        
        # Load model in background
        self._load_model_async()
    
    def _create_widgets(self):
        """Create all UI widgets."""
        
        # Main container
        self.main_frame = ctk.CTkFrame(self)
        
        # Top controls frame
        self.controls_frame = ctk.CTkFrame(self.main_frame)
        
        # Record button
        self.record_button = ctk.CTkButton(
            self.controls_frame,
            text="🎤 Start Recording",
            command=self._toggle_recording,
            width=160,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        
        # Upload button
        self.upload_button = ctk.CTkButton(
            self.controls_frame,
            text="📁 Upload Files",
            command=self._upload_files,
            width=140,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        
        # Recording indicator
        self.recording_indicator = RecordingIndicator(self.controls_frame)
        
        # Settings frame
        self.settings_frame = ctk.CTkFrame(self.main_frame)
        
        # Language selector
        self.language_selector = LanguageSelector(
            self.settings_frame,
            on_change=self._on_language_change
        )
        self.language_selector.set(self.config.language)
        
        # Timestamp toggle
        self.timestamp_toggle = TimestampToggle(
            self.settings_frame,
            on_change=self._on_timestamp_toggle
        )
        self.timestamp_toggle.set(self.config.timestamps_enabled)
        
        # Preview frame with label
        self.preview_frame = ctk.CTkFrame(self.main_frame)
        
        self.preview_label = ctk.CTkLabel(
            self.preview_frame,
            text="Transcription Preview",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        
        # Transcription preview
        self.preview = TranscriptionPreview(self.preview_frame)
        
        # Progress frame
        self.progress_frame = ProgressFrame(self.main_frame)
        
        # Bottom controls
        self.bottom_frame = ctk.CTkFrame(self.main_frame)
        
        # Clear button
        self.clear_button = ctk.CTkButton(
            self.bottom_frame,
            text="🗑️ Clear",
            command=self._clear_transcription,
            width=100,
            fg_color="gray",
            hover_color="darkgray"
        )
        
        # Save button
        self.save_button = ctk.CTkButton(
            self.bottom_frame,
            text="💾 Save to File",
            command=self._save_transcription,
            width=140,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        
        # Status bar
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Loading speech recognition model...",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
    
    def _create_layout(self):
        """Arrange widgets in the window."""
        
        # Configure main grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main frame
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)  # Preview expands
        
        # Controls frame (row 0)
        self.controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.record_button.pack(side="left", padx=(0, 10))
        self.upload_button.pack(side="left", padx=(0, 20))
        self.recording_indicator.pack(side="left", padx=10)
        
        # Settings frame (row 1)
        self.settings_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.language_selector.pack(side="left", padx=(0, 30))
        self.timestamp_toggle.pack(side="left")
        
        # Preview frame (row 2)
        self.preview_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(1, weight=1)
        
        self.preview_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.preview.grid(row=1, column=0, sticky="nsew")
        
        # Progress frame (row 3)
        self.progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        
        # Bottom frame (row 4)
        self.bottom_frame.grid(row=4, column=0, sticky="ew", pady=(0, 5))
        self.clear_button.pack(side="left", padx=(0, 10))
        self.save_button.pack(side="right")
        
        # Status bar (row 5)
        self.status_label.grid(row=5, column=0, sticky="w")
    
    def _bind_events(self):
        """Bind keyboard and window events."""
        self.bind("<Control-s>", lambda e: self._save_transcription())
        self.bind("<Escape>", lambda e: self._stop_recording() if self._is_recording else None)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _load_model_async(self):
        """Load the transcription model in a background thread."""
        def load():
            success = self.engine.load_model(
                progress_callback=lambda msg: self.after(0, lambda: self._update_status(msg))
            )
            if success:
                self.after(0, lambda: self._update_status("Ready - Model loaded"))
            else:
                error = self.engine.get_load_error()
                self.after(0, lambda: self._update_status(f"Error: {error}"))
        
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
    
    def _update_status(self, message: str):
        """Update the status bar text."""
        self.status_label.configure(text=message)
    
    def _toggle_recording(self):
        """Toggle recording on/off."""
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()
    
    def _start_recording(self):
        """Start audio recording."""
        if self._is_processing:
            messagebox.showwarning("Busy", "Please wait for processing to complete.")
            return
        
        if not self.engine.is_model_loaded():
            messagebox.showwarning("Not Ready", "Please wait for the model to load.")
            return
        
        # Create recorder with chunk callback
        self._recorder = AudioRecorder(
            chunk_callback=self._on_audio_chunk,
            chunk_duration=1.5,
            overlap_duration=0.5
        )
        
        if self._recorder.start_recording():
            self._is_recording = True
            self._transcription_segments = []
            self.preview.clear()
            
            # Update UI
            self.record_button.configure(
                text="⏹️ Stop Recording",
                fg_color="red",
                hover_color="darkred"
            )
            self.recording_indicator.set_recording(True)
            self.recording_indicator.update_duration(0)
            
            # Disable settings during recording
            self.upload_button.configure(state="disabled")
            self.timestamp_toggle.disable()
            
            # Start duration updates
            self._update_recording_duration()
            
            self._update_status("Recording... Speak now")
        else:
            messagebox.showerror("Error", "Failed to start recording. Check your microphone.")
    
    def _stop_recording(self):
        """Stop audio recording and process the result."""
        if not self._is_recording or not self._recorder:
            return
        
        self._is_recording = False
        
        # Stop duration updates
        if self._duration_update_job:
            self.after_cancel(self._duration_update_job)
            self._duration_update_job = None
        
        # Update UI immediately
        self.record_button.configure(
            text="🎤 Start Recording",
            fg_color=["#3B8ED0", "#1F6AA5"],  # Default blue
            hover_color=["#36719F", "#144870"]
        )
        self.recording_indicator.set_recording(False)
        
        # Stop recording and get audio file
        audio_path = self._recorder.stop_recording()
        
        if audio_path:
            self._current_audio_path = audio_path
            # Process the full recording
            self._process_audio_file(audio_path)
        else:
            self._update_status("No audio recorded")
            self.upload_button.configure(state="normal")
            self.timestamp_toggle.enable()
    
    def _update_recording_duration(self):
        """Update the recording duration display."""
        if self._is_recording and self._recorder:
            duration = self._recorder.get_recording_duration()
            self.recording_indicator.update_duration(duration)
            self.recording_indicator.blink()
            
            # Schedule next update
            self._duration_update_job = self.after(500, self._update_recording_duration)
    
    def _on_audio_chunk(self, chunk):
        """Handle audio chunk for real-time preview."""
        if not self._is_recording:
            return
        
        # Transcribe chunk in background
        def process_chunk():
            language = self.language_selector.get()
            text = self.engine.transcribe_chunk(chunk, language)
            if text:
                self.after(0, lambda: self.preview.set_provisional_text(text))
        
        thread = threading.Thread(target=process_chunk, daemon=True)
        thread.start()
    
    def _upload_files(self):
        """Open file dialog to upload one or more audio/video files."""
        if self._is_recording or self._is_processing:
            return
        
        initial_dir = self.config.last_upload_directory or None
        
        # Use askopenfilenames for multiple file selection
        file_paths = filedialog.askopenfilenames(
            title="Select Audio/Video Files",
            initialdir=initial_dir,
            filetypes=get_file_dialog_filetypes()
        )
        
        if file_paths:
            # Convert to Path objects
            paths = [Path(fp) for fp in file_paths]
            
            # Save directory for next time
            self.config.last_upload_directory = str(paths[0].parent)
            
            # Clear previous state
            self.preview.clear()
            self._batch_transcriptions = {}
            self._temp_audio_files = []
            
            if len(paths) == 1:
                # Single file - use existing flow
                self._current_audio_path = paths[0]
                self._batch_files = []
                self._process_single_file(paths[0])
            else:
                # Multiple files - use batch processing
                self._batch_files = paths
                self._current_file_index = 0
                self._start_batch_processing()
    
    def _process_single_file(self, file_path: Path):
        """Process a single audio or video file."""
        self._is_processing = True
        self._transcription_segments = []
        
        # Update UI
        self.record_button.configure(state="disabled")
        self.upload_button.configure(state="disabled")
        self.timestamp_toggle.disable()
        self.save_button.configure(state="disabled")
        
        self.progress_frame.show()
        self.progress_frame.set_indeterminate()
        
        if is_video_file(file_path):
            self._update_status(f"Extracting audio from {file_path.name}...")
            self.progress_frame.set_progress(0, f"Extracting audio from video...")
        else:
            self._update_status(f"Processing {file_path.name}...")
            self.progress_frame.set_progress(0, "Preparing audio...")
        
        # Prepare and transcribe in background
        def process():
            try:
                # Prepare file (extract audio from video if needed)
                audio_path, error, is_temp = prepare_file_for_transcription(
                    file_path,
                    progress_callback=lambda msg: self.after(0, lambda: self._update_status(msg))
                )
                
                if error:
                    self.after(0, lambda: self._on_transcription_error(error))
                    return
                
                if is_temp and audio_path:
                    self._temp_audio_files.append(audio_path)
                
                self._current_audio_path = audio_path
                
                # Now transcribe
                self.after(0, lambda: self.progress_frame.set_determinate())
                self.after(0, lambda: self._update_status("Transcribing..."))
                
                language = self.language_selector.get()
                include_timestamps = self.timestamp_toggle.get()
                
                segments = list(self.engine.transcribe_file(
                    audio_path,
                    language=language,
                    include_timestamps=include_timestamps,
                    progress_callback=lambda p, t: self.after(
                        0, lambda: self._on_transcription_progress(p, t)
                    )
                ))
                
                self._transcription_segments = segments
                self.after(0, self._on_transcription_complete)
                
            except Exception as e:
                self.after(0, lambda: self._on_transcription_error(str(e)))
        
        thread = threading.Thread(target=process, daemon=True)
        thread.start()
    
    def _start_batch_processing(self):
        """Start batch processing of multiple files."""
        self._is_processing = True
        total_files = len(self._batch_files)
        
        # Ask user for output directory
        output_dir = filedialog.askdirectory(
            title="Select Output Folder for Transcriptions",
            initialdir=self.config.last_save_directory or str(self._batch_files[0].parent)
        )
        
        if not output_dir:
            # User cancelled
            self._is_processing = False
            return
        
        self._batch_output_dir = Path(output_dir)
        self.config.last_save_directory = output_dir
        
        # Update UI
        self.record_button.configure(state="disabled")
        self.upload_button.configure(state="disabled")
        self.timestamp_toggle.disable()
        self.save_button.configure(state="disabled")
        
        self.progress_frame.show()
        self._update_status(f"Processing {total_files} files → {self._batch_output_dir.name}/")
        
        # Start processing first file
        self._process_next_batch_file()
    
    def _process_next_batch_file(self):
        """Process the next file in the batch."""
        if self._current_file_index >= len(self._batch_files):
            # All files processed
            self._on_batch_complete()
            return
        
        current_file = self._batch_files[self._current_file_index]
        file_num = self._current_file_index + 1
        total_files = len(self._batch_files)
        
        self.progress_frame.set_indeterminate()
        self._update_status(f"[{file_num}/{total_files}] Processing {current_file.name}...")
        
        def process():
            try:
                # Prepare file (extract audio from video if needed)
                audio_path, error, is_temp = prepare_file_for_transcription(
                    current_file,
                    progress_callback=lambda msg: self.after(
                        0, lambda m=msg: self._update_status(f"[{file_num}/{total_files}] {m}")
                    )
                )
                
                if error:
                    # Store error message for this file
                    self._batch_transcriptions[current_file.name] = f"[ERROR: {error}]"
                    self.after(0, self._advance_batch)
                    return
                
                if is_temp and audio_path:
                    self._temp_audio_files.append(audio_path)
                
                # Transcribe
                self.after(0, lambda: self.progress_frame.set_determinate())
                self.after(0, lambda: self._update_status(f"[{file_num}/{total_files}] Transcribing {current_file.name}..."))
                
                language = self.language_selector.get()
                include_timestamps = self.timestamp_toggle.get()
                
                segments = list(self.engine.transcribe_file(
                    audio_path,
                    language=language,
                    include_timestamps=include_timestamps,
                    progress_callback=lambda p, t: self.after(
                        0, lambda: self.progress_frame.set_progress(p, f"[{file_num}/{total_files}] Transcribing... {int(p*100)}%")
                    )
                ))
                
                # Format and store transcription
                formatted_text = self.engine.format_transcription(segments, include_timestamps)
                self._batch_transcriptions[current_file.name] = formatted_text
                
                # Save transcription to individual file
                output_filename = current_file.stem + ".txt"
                output_path = self._batch_output_dir / output_filename
                try:
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(formatted_text)
                    self._batch_transcriptions[current_file.name] = f"✓ Saved to {output_filename}"
                except Exception as save_error:
                    self._batch_transcriptions[current_file.name] = f"[SAVE ERROR: {str(save_error)}]"
                
                # Update preview with this file's transcription
                self.after(0, lambda: self._update_batch_preview())
                
                # Advance to next file
                self.after(0, self._advance_batch)
                
            except Exception as e:
                self._batch_transcriptions[current_file.name] = f"[ERROR: {str(e)}]"
                self.after(0, self._advance_batch)
        
        thread = threading.Thread(target=process, daemon=True)
        thread.start()
    
    def _advance_batch(self):
        """Advance to the next file in the batch."""
        self._current_file_index += 1
        self._process_next_batch_file()
    
    def _update_batch_preview(self):
        """Update the preview with all batch transcriptions so far."""
        lines = []
        for filename, text in self._batch_transcriptions.items():
            lines.append(f"=== {filename} ===")
            lines.append(text)
            lines.append("")  # Empty line between files
        
        combined_text = "\n".join(lines)
        self.preview.set_final_text(combined_text)
    
    def _on_batch_complete(self):
        """Handle completion of batch processing."""
        self._is_processing = False
        
        # Clean up temp files
        for temp_file in self._temp_audio_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass
        self._temp_audio_files = []
        
        # Final update of preview
        self._update_batch_preview()
        
        # Update UI
        self.progress_frame.hide()
        self.record_button.configure(state="normal")
        self.upload_button.configure(state="normal")
        self.timestamp_toggle.enable()
        self.save_button.configure(state="normal")
        
        total_files = len(self._batch_files)
        success_count = sum(1 for t in self._batch_transcriptions.values() if t.startswith("✓"))
        
        self._update_status(f"Batch complete - {success_count}/{total_files} files saved to {self._batch_output_dir.name}/")
        
        # Show completion message
        if success_count > 0:
            messagebox.showinfo(
                "Batch Complete",
                f"Transcribed {success_count}/{total_files} files.\n\nSaved to:\n{self._batch_output_dir}"
            )
    
    def _process_audio_file(self, audio_path: Path):
        """Process an audio file for transcription (legacy method, now calls _process_single_file)."""
        self._process_single_file(audio_path)
    
    def _on_transcription_progress(self, progress: float, text: str):
        """Handle transcription progress update."""
        percent = int(progress * 100)
        self.progress_frame.set_progress(progress, f"Transcribing... {percent}%")
        
        # Update preview with accumulated text
        if text:
            self.preview.append_final_text(text)
    
    def _on_transcription_complete(self):
        """Handle transcription completion."""
        self._is_processing = False
        
        # Clean up temp files
        for temp_file in self._temp_audio_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass
        self._temp_audio_files = []
        
        # Format final text
        include_timestamps = self.timestamp_toggle.get()
        final_text = self.engine.format_transcription(
            self._transcription_segments,
            include_timestamps=include_timestamps
        )
        
        # Update preview with final formatted text
        self.preview.set_final_text(final_text)
        
        # Update UI
        self.progress_frame.hide()
        self.record_button.configure(state="normal")
        self.upload_button.configure(state="normal")
        self.timestamp_toggle.enable()
        self.save_button.configure(state="normal")
        
        word_count = len(final_text.split()) if final_text else 0
        self._update_status(f"Transcription complete - {word_count} words")
    
    def _on_transcription_error(self, error: str):
        """Handle transcription error."""
        self._is_processing = False
        
        self.progress_frame.hide()
        self.record_button.configure(state="normal")
        self.upload_button.configure(state="normal")
        self.timestamp_toggle.enable()
        
        self._update_status(f"Error: {error}")
        messagebox.showerror("Transcription Error", f"Failed to transcribe audio:\n{error}")
    
    def _clear_transcription(self):
        """Clear the current transcription."""
        self.preview.clear()
        self._transcription_segments = []
        self._current_audio_path = None
        self._update_status("Cleared")
    
    def _save_transcription(self):
        """Save the transcription to a file."""
        text = self.preview.get_text()
        
        if not text.strip():
            messagebox.showwarning("Nothing to Save", "There is no transcription to save.")
            return
        
        initial_dir = self.config.last_save_directory or None
        
        file_path = filedialog.asksaveasfilename(
            title="Save Transcription",
            initialdir=initial_dir,
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ],
            initialfile="transcription.txt"
        )
        
        if file_path:
            try:
                save_path = Path(file_path)
                self.config.last_save_directory = str(save_path.parent)
                
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(text)
                
                self._update_status(f"Saved to {save_path.name}")
                messagebox.showinfo("Saved", f"Transcription saved to:\n{save_path}")
                
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file:\n{e}")
    
    def _on_language_change(self, language: str):
        """Handle language selection change."""
        self.config.language = language
    
    def _on_timestamp_toggle(self, enabled: bool):
        """Handle timestamp toggle change."""
        self.config.timestamps_enabled = enabled
    
    def _on_close(self):
        """Handle window close."""
        if self._is_recording:
            self._recorder.stop_recording()
        
        # Clean up temp files
        clean_temp_files()
        
        self.destroy()


def run_app():
    """Run the application."""
    app = SpeechToTextApp()
    app.mainloop()
