# gui_typer.py
# A small GUI to paste text/code and have it typed into another window (e.g., VirtualBox)
# Requirements: pip install pyautogui

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pyautogui

COUNTDOWN_SECONDS = 5

class TyperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple Typer")
        self.geometry("700x450")
        self.minsize(600, 380)

        # ----- Widgets -----
        # Text label
        ttk.Label(self, text="Paste your text/code below:").pack(anchor="w", padx=12, pady=(12, 4))

        # Big text area
        self.txt = tk.Text(self, wrap="word", undo=True, height=16, font=("Consolas", 11))
        self.txt.pack(fill="both", expand=True, padx=12)
        self.txt.focus_set()

        # Options row
        options = ttk.Frame(self)
        options.pack(fill="x", padx=12, pady=8)

        ttk.Label(options, text="Typing delay (seconds per character):").pack(side="left")
        self.delay_var = tk.StringVar(value="0.05")
        self.delay_entry = ttk.Spinbox(options, from_=0.0, to=1.0, increment=0.01, textvariable=self.delay_var, width=6)
        self.delay_entry.pack(side="left", padx=(6, 16))

        self.minimize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options, text="Minimize during countdown", variable=self.minimize_var).pack(side="left")

        # Status + buttons
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=12, pady=(0, 12))

        self.status = ttk.Label(bottom, text="Ready.", foreground="#444")
        self.status.pack(side="left")

        self.type_button = ttk.Button(bottom, text="Type", command=self.on_type_clicked)
        self.type_button.pack(side="right")

        self.cancel_button = ttk.Button(bottom, text="Cancel", command=self.cancel_action, state="disabled")
        self.cancel_button.pack(side="right", padx=(0, 8))

        # Internal state
        self._countdown_remaining = 0
        self._cancel_requested = False
        self._is_typing = False

    def on_type_clicked(self):
        text = self.txt.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("Nothing to type", "Please paste some text/code first.")
            return

        # Parse delay
        try:
            delay = float(self.delay_var.get())
            if delay < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid delay", "Please enter a non-negative number for the typing delay.")
            return

        # Disable UI during countdown/typing
        self._cancel_requested = False
        self._is_typing = False
        self._text_to_type = text
        self._delay = delay

        self.type_button.config(state="disabled")
        self.cancel_button.config(state="normal")

        self._countdown_remaining = COUNTDOWN_SECONDS
        self.status.config(text=f"Click into your VirtualBox window… starting in {self._countdown_remaining}s")
        if self.minimize_var.get():
            # Minimize so keystrokes don't land here
            self.after(150, self.iconify)

        self.after(1000, self._tick_countdown)

    def _tick_countdown(self):
        if self._cancel_requested:
            self._reset_ui("Canceled.")
            return

        self._countdown_remaining -= 1
        if self._countdown_remaining > 0:
            self.status.config(text=f"Starting in {self._countdown_remaining}s…")
            self.after(1000, self._tick_countdown)
        else:
            self.status.config(text="Typing…")
            self._is_typing = True
            # Run typing in a thread so the UI stays responsive
            threading.Thread(target=self._do_typing, daemon=True).start()

    def _do_typing(self):
        try:
            # Small extra buffer to allow focus switch if not minimized
            # (No sleep here; countdown already provided time.)
            if self._cancel_requested:
                self._reset_ui("Canceled.")
                return
            pyautogui.typewrite(self._text_to_type, interval=self._delay)
            self.after(0, lambda: self._reset_ui("Done typing."))
        except Exception as e:
            self.after(0, lambda: self._reset_ui(f"Error: {e}"))

    def cancel_action(self):
        # If countdown or typing is underway, request cancel
        self._cancel_requested = True

    def _reset_ui(self, msg):
        self._is_typing = False
        self.type_button.config(state="normal")
        self.cancel_button.config(state="disabled")
        try:
            # Restore window if minimized
            self.deiconify()
        except:
            pass
        self.status.config(text=msg)

if __name__ == "__main__":
    app = TyperApp()
    app.mainloop()
