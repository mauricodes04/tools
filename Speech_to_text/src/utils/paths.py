"""
Portable path utilities for USB deployment.
Handles path resolution relative to the application root.
"""

import os
import sys
from pathlib import Path


def get_app_root() -> Path:
    """
    Get the application root directory.
    Works both when running from source and when packaged with PyInstaller.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running from source
        return Path(__file__).parent.parent.parent


def get_models_dir() -> Path:
    """Get the directory where Whisper models are stored."""
    models_dir = get_app_root() / "models"
    models_dir.mkdir(exist_ok=True)
    return models_dir


def get_resources_dir() -> Path:
    """Get the directory where resources (icons, images) are stored."""
    return get_app_root() / "resources"


def get_config_dir() -> Path:
    """Get the directory where configuration files are stored."""
    config_dir = get_app_root() / "config"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_temp_dir() -> Path:
    """Get a temporary directory for audio recordings."""
    temp_dir = get_app_root() / "temp"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir


def get_config_file() -> Path:
    """Get the path to the main configuration file."""
    return get_config_dir() / "settings.ini"


def clean_temp_files():
    """Remove temporary files from the temp directory."""
    temp_dir = get_temp_dir()
    for file in temp_dir.glob("*.wav"):
        try:
            file.unlink()
        except Exception:
            pass  # Ignore errors when cleaning up
