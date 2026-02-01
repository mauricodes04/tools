"""
Configuration management for persisting user settings.
"""

import configparser
from pathlib import Path
from typing import Optional

from .paths import get_config_file


class Config:
    """Manages application configuration with INI file persistence."""
    
    DEFAULT_SETTINGS = {
        "General": {
            "language": "English",
            "timestamps_enabled": "False",
            "last_save_directory": "",
            "last_upload_directory": "",
        },
        "Audio": {
            "sample_rate": "16000",
            "channels": "1",
        },
        "Transcription": {
            "model_size": "small",
            "compute_type": "int8",
            "cpu_threads": "0",  # 0 = auto (use all cores)
            "num_workers": "1",   # Number of parallel workers
        }
    }
    
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_path = get_config_file()
        self._load_or_create()
    
    def _load_or_create(self):
        """Load existing config or create with defaults."""
        if self.config_path.exists():
            self.config.read(self.config_path, encoding="utf-8")
            # Ensure all default sections and keys exist
            for section, values in self.DEFAULT_SETTINGS.items():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                for key, default_value in values.items():
                    if not self.config.has_option(section, key):
                        self.config.set(section, key, default_value)
        else:
            # Create new config with defaults
            for section, values in self.DEFAULT_SETTINGS.items():
                self.config.add_section(section)
                for key, value in values.items():
                    self.config.set(section, key, value)
            self.save()
    
    def save(self):
        """Save configuration to file."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            self.config.write(f)
    
    def get(self, section: str, key: str, fallback: Optional[str] = None) -> str:
        """Get a configuration value."""
        return self.config.get(section, key, fallback=fallback or "")
    
    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get a boolean configuration value."""
        return self.config.getboolean(section, key, fallback=fallback)
    
    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """Get an integer configuration value."""
        return self.config.getint(section, key, fallback=fallback)
    
    def set(self, section: str, key: str, value: str):
        """Set a configuration value and save."""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        self.save()
    
    # Convenience properties
    @property
    def language(self) -> str:
        return self.get("General", "language", "English")
    
    @language.setter
    def language(self, value: str):
        self.set("General", "language", value)
    
    @property
    def timestamps_enabled(self) -> bool:
        return self.get_bool("General", "timestamps_enabled", False)
    
    @timestamps_enabled.setter
    def timestamps_enabled(self, value: bool):
        self.set("General", "timestamps_enabled", str(value))
    
    @property
    def last_save_directory(self) -> str:
        return self.get("General", "last_save_directory", "")
    
    @last_save_directory.setter
    def last_save_directory(self, value: str):
        self.set("General", "last_save_directory", value)
    
    @property
    def last_upload_directory(self) -> str:
        return self.get("General", "last_upload_directory", "")
    
    @last_upload_directory.setter
    def last_upload_directory(self, value: str):
        self.set("General", "last_upload_directory", value)
    
    @property
    def sample_rate(self) -> int:
        return self.get_int("Audio", "sample_rate", 16000)
    
    @property
    def model_size(self) -> str:
        return self.get("Transcription", "model_size", "small")
    
    @property
    def compute_type(self) -> str:
        return self.get("Transcription", "compute_type", "int8")
    
    @property
    def cpu_threads(self) -> int:
        return self.get_int("Transcription", "cpu_threads", 0)
    
    @property
    def num_workers(self) -> int:
        return self.get_int("Transcription", "num_workers", 1)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
