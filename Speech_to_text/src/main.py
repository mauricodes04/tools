"""
Speech to Text - Portable USB Application

A portable speech-to-text application that records audio or accepts uploaded
audio files and converts them to text using OpenAI Whisper (via faster-whisper).

Supports English and Spanish languages with optional timestamp insertion.
"""

import sys
import os

# Fix OpenMP duplicate library conflict (numpy/onnxruntime/ctranslate2)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
# Suppress huggingface symlink warning on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Ensure the src directory is in the path when running from source
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    APP_DIR = os.path.dirname(sys.executable)
else:
    # Running from source
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, APP_DIR)


def main():
    """Main entry point for the application."""
    # Import here to ensure path is set up
    from src.gui.app import run_app
    
    print("Starting Speech to Text application...")
    run_app()


if __name__ == "__main__":
    main()
