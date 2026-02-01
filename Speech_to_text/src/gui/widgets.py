"""
Custom GUI widgets for the Speech-to-Text application.
"""

import customtkinter as ctk
from typing import Optional, Callable


class TranscriptionPreview(ctk.CTkFrame):
    """
    A text preview widget that shows transcription with provisional/final styling.
    Provisional text is shown in italic gray, final text in normal black.
    """
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create scrollable text area
        self.textbox = ctk.CTkTextbox(
            self,
            wrap="word",
            font=ctk.CTkFont(size=14),
            state="disabled"
        )
        self.textbox.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        # Track provisional text position
        self._provisional_start: Optional[str] = None
        self._final_text = ""
    
    def set_final_text(self, text: str):
        """Set the final (confirmed) transcription text."""
        self._final_text = text
        self._update_display()
    
    def set_provisional_text(self, text: str):
        """Set the provisional (in-progress) transcription text."""
        self._update_display(provisional=text)
    
    def append_final_text(self, text: str):
        """Append text to the final transcription."""
        if self._final_text and not self._final_text.endswith(" "):
            self._final_text += " "
        self._final_text += text
        self._update_display()
    
    def clear(self):
        """Clear all text."""
        self._final_text = ""
        self._provisional_start = None
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
    
    def _update_display(self, provisional: str = ""):
        """Update the display with final and provisional text."""
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        
        # Insert final text
        if self._final_text:
            self.textbox.insert("end", self._final_text)
        
        # Insert provisional text with different styling
        if provisional:
            if self._final_text and not self._final_text.endswith(" "):
                self.textbox.insert("end", " ")
            
            # Note: CTkTextbox doesn't support tags easily, so we just show the text
            # In a full implementation, you might use a tk.Text widget for styling
            self.textbox.insert("end", f"[{provisional}]")
        
        # Scroll to end
        self.textbox.see("end")
        self.textbox.configure(state="disabled")
    
    def get_text(self) -> str:
        """Get the current final text."""
        return self._final_text


class RecordingIndicator(ctk.CTkFrame):
    """
    Visual indicator showing recording status with duration.
    """
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        
        # Recording dot indicator
        self.indicator_dot = ctk.CTkLabel(
            self,
            text="●",
            font=ctk.CTkFont(size=20),
            text_color="gray"
        )
        self.indicator_dot.grid(row=0, column=0, padx=(0, 10))
        
        # Duration label
        self.duration_label = ctk.CTkLabel(
            self,
            text="00:00",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.duration_label.grid(row=0, column=1, sticky="w")
        
        self._is_recording = False
        self._blink_state = False
    
    def set_recording(self, is_recording: bool):
        """Set the recording state."""
        self._is_recording = is_recording
        if is_recording:
            self.indicator_dot.configure(text_color="red")
        else:
            self.indicator_dot.configure(text_color="gray")
            self._blink_state = False
    
    def update_duration(self, seconds: float):
        """Update the duration display."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        self.duration_label.configure(text=f"{minutes:02d}:{secs:02d}")
    
    def blink(self):
        """Toggle the recording indicator for blinking effect."""
        if self._is_recording:
            self._blink_state = not self._blink_state
            color = "red" if self._blink_state else "darkred"
            self.indicator_dot.configure(text_color=color)


class ProgressFrame(ctk.CTkFrame):
    """
    Progress indicator with label and progress bar.
    """
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=1, column=0, sticky="ew")
        self.progress_bar.set(0)
        
        # Hide by default
        self.grid_remove()
    
    def show(self):
        """Show the progress frame."""
        self.grid()
    
    def hide(self):
        """Hide the progress frame."""
        self.grid_remove()
    
    def set_progress(self, value: float, status: str = ""):
        """Set progress value (0-1) and optional status text."""
        self.progress_bar.set(value)
        if status:
            self.status_label.configure(text=status)
    
    def set_indeterminate(self, status: str = "Processing..."):
        """Set progress bar to indeterminate mode."""
        self.status_label.configure(text=status)
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
    
    def set_determinate(self):
        """Set progress bar to determinate mode."""
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)


class LanguageSelector(ctk.CTkFrame):
    """
    Language selection dropdown with label.
    """
    
    LANGUAGES = ["English", "Spanish"]
    
    def __init__(
        self,
        master,
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        
        self.on_change = on_change
        
        # Label
        self.label = ctk.CTkLabel(
            self,
            text="Language:",
            font=ctk.CTkFont(size=12)
        )
        self.label.grid(row=0, column=0, padx=(0, 10))
        
        # Dropdown
        self.dropdown = ctk.CTkComboBox(
            self,
            values=self.LANGUAGES,
            command=self._on_selection_change,
            state="readonly",
            width=120
        )
        self.dropdown.set("English")
        self.dropdown.grid(row=0, column=1)
    
    def _on_selection_change(self, value: str):
        """Handle selection change."""
        if self.on_change:
            self.on_change(value)
    
    def get(self) -> str:
        """Get the currently selected language."""
        return self.dropdown.get()
    
    def set(self, language: str):
        """Set the selected language."""
        if language in self.LANGUAGES:
            self.dropdown.set(language)


class TimestampToggle(ctk.CTkFrame):
    """
    Checkbox for enabling/disabling timestamps in output.
    """
    
    def __init__(
        self,
        master,
        on_change: Optional[Callable[[bool], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        
        self.on_change = on_change
        self._enabled = ctk.BooleanVar(value=False)
        
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="Include timestamps [HH:MM:SS]",
            variable=self._enabled,
            command=self._on_toggle,
            font=ctk.CTkFont(size=12)
        )
        self.checkbox.grid(row=0, column=0)
    
    def _on_toggle(self):
        """Handle toggle change."""
        if self.on_change:
            self.on_change(self._enabled.get())
    
    def get(self) -> bool:
        """Get the current toggle state."""
        return self._enabled.get()
    
    def set(self, enabled: bool):
        """Set the toggle state."""
        self._enabled.set(enabled)
    
    def enable(self):
        """Enable the checkbox."""
        self.checkbox.configure(state="normal")
    
    def disable(self):
        """Disable the checkbox (during recording)."""
        self.checkbox.configure(state="disabled")
