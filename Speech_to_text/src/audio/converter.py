"""
Audio/Video converter module for extracting and converting audio from various file formats.
Supports extracting audio from video files (MP4, MKV, AVI, etc.) and converting audio formats.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple
import tempfile

from ..utils.paths import get_temp_dir


# Supported file extensions
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.wma', '.aac'}
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mpeg', '.mpg', '.m4v'}
ALL_SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def is_audio_file(file_path: Path) -> bool:
    """Check if the file is a supported audio format."""
    return file_path.suffix.lower() in AUDIO_EXTENSIONS


def is_video_file(file_path: Path) -> bool:
    """Check if the file is a supported video format."""
    return file_path.suffix.lower() in VIDEO_EXTENSIONS


def is_supported_file(file_path: Path) -> bool:
    """Check if the file is a supported audio or video format."""
    return file_path.suffix.lower() in ALL_SUPPORTED_EXTENSIONS


def find_ffmpeg() -> Optional[str]:
    """
    Find ffmpeg executable in the system.
    
    Returns:
        Path to ffmpeg executable or None if not found.
    """
    # Check if ffmpeg is in PATH
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path
    
    # Common Windows locations
    common_paths = [
        Path('C:/ffmpeg/bin/ffmpeg.exe'),
        Path('C:/Program Files/ffmpeg/bin/ffmpeg.exe'),
        Path('C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe'),
    ]
    
    for path in common_paths:
        if path.exists():
            return str(path)
    
    return None


def extract_audio_from_video(
    video_path: Path,
    output_format: str = 'wav',
    sample_rate: int = 16000,
    progress_callback: Optional[callable] = None
) -> Tuple[Optional[Path], Optional[str]]:
    """
    Extract audio from a video file using ffmpeg.
    
    Args:
        video_path: Path to the video file
        output_format: Output audio format (default: wav for whisper)
        sample_rate: Sample rate for the output audio (default: 16000 for whisper)
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of (output_path, error_message). If successful, error is None.
    """
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return None, "FFmpeg not found. Please install FFmpeg and add it to PATH."
    
    if not video_path.exists():
        return None, f"Video file not found: {video_path}"
    
    # Create output path in temp directory
    temp_dir = get_temp_dir()
    output_filename = f"{video_path.stem}_audio.{output_format}"
    output_path = temp_dir / output_filename
    
    try:
        if progress_callback:
            progress_callback(f"Extracting audio from {video_path.name}...")
        
        # Build ffmpeg command
        cmd = [
            ffmpeg_path,
            '-i', str(video_path),  # Input file
            '-vn',  # No video
            '-acodec', 'pcm_s16le' if output_format == 'wav' else 'libmp3lame',
            '-ar', str(sample_rate),  # Sample rate
            '-ac', '1',  # Mono channel
            '-y',  # Overwrite output
            str(output_path)
        ]
        
        # Run ffmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or "Unknown ffmpeg error"
            return None, f"FFmpeg error: {error_msg[:200]}"
        
        if not output_path.exists():
            return None, "Audio extraction failed - output file not created"
        
        if progress_callback:
            progress_callback(f"Audio extracted from {video_path.name}")
        
        return output_path, None
        
    except Exception as e:
        return None, f"Error extracting audio: {str(e)}"


def convert_audio_file(
    audio_path: Path,
    output_format: str = 'wav',
    sample_rate: int = 16000,
    progress_callback: Optional[callable] = None
) -> Tuple[Optional[Path], Optional[str]]:
    """
    Convert an audio file to a format suitable for transcription.
    
    Args:
        audio_path: Path to the audio file
        output_format: Output audio format
        sample_rate: Sample rate for the output audio
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of (output_path, error_message). If successful, error is None.
    """
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        # If no ffmpeg, return original path and hope faster-whisper can handle it
        return audio_path, None
    
    if not audio_path.exists():
        return None, f"Audio file not found: {audio_path}"
    
    # If already wav, just return it
    if audio_path.suffix.lower() == '.wav':
        return audio_path, None
    
    # Create output path in temp directory
    temp_dir = get_temp_dir()
    output_filename = f"{audio_path.stem}_converted.{output_format}"
    output_path = temp_dir / output_filename
    
    try:
        if progress_callback:
            progress_callback(f"Converting {audio_path.name}...")
        
        cmd = [
            ffmpeg_path,
            '-i', str(audio_path),
            '-acodec', 'pcm_s16le',
            '-ar', str(sample_rate),
            '-ac', '1',
            '-y',
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if result.returncode != 0:
            # Fallback to original file
            return audio_path, None
        
        if not output_path.exists():
            return audio_path, None
        
        return output_path, None
        
    except Exception as e:
        # Fallback to original file on any error
        return audio_path, None


def prepare_file_for_transcription(
    file_path: Path,
    progress_callback: Optional[callable] = None
) -> Tuple[Optional[Path], Optional[str], bool]:
    """
    Prepare any audio or video file for transcription.
    
    Args:
        file_path: Path to the audio or video file
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of (audio_path, error_message, is_temp_file).
        is_temp_file indicates whether the returned path is a temp file that should be cleaned up.
    """
    if is_video_file(file_path):
        # Extract audio from video
        audio_path, error = extract_audio_from_video(
            file_path,
            progress_callback=progress_callback
        )
        return audio_path, error, True if audio_path else False
    
    elif is_audio_file(file_path):
        # Convert if needed
        audio_path, error = convert_audio_file(
            file_path,
            progress_callback=progress_callback
        )
        # Check if conversion happened (different path)
        is_temp = audio_path != file_path if audio_path else False
        return audio_path, error, is_temp
    
    else:
        return None, f"Unsupported file format: {file_path.suffix}", False


def get_file_dialog_filetypes() -> list:
    """
    Get the file types for the file dialog.
    
    Returns:
        List of tuples (description, pattern) for file dialog.
    """
    return [
        ("All supported files", "*.wav *.mp3 *.flac *.m4a *.ogg *.wma *.aac *.mp4 *.mkv *.avi *.mov *.wmv *.webm"),
        ("Video files", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.mpeg *.mpg *.m4v"),
        ("Audio files", "*.wav *.mp3 *.flac *.m4a *.ogg *.wma *.aac"),
        ("MP4 files", "*.mp4"),
        ("WAV files", "*.wav"),
        ("MP3 files", "*.mp3"),
        ("All files", "*.*")
    ]
