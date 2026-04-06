| Tool | Description | GUI |
|------|-------------|-----|
| [OCRTool](OCRTool/) | Extract text from images and PDFs using Tesseract OCR | ✅ PyQt6 |
| [Speech_to_text](Speech_to_text/) | Record or upload audio/video and transcribe to text using Whisper | ✅ CustomTkinter |
| [Typer](Typer/) | Type text automatically into another window (useful for VMs) | ✅ Tkinter |
| [Rockyou](Rockyou/) | Record keyboard/mouse actions and replay with password list | ❌ Console |


```bash
pip install -r requirements.txt
```

### Run Individual Tools

Each tool can be run directly:

```bash
# OCRTool - Text extraction from images/PDFs
cd OCRTool
python main.py

# Speech to Text - Audio/Video transcription
cd Speech_to_text/src
python main.py

# Typer - Auto-type text into windows
cd Typer
python typer.py

# Rockyou - Password replay tool
cd Rockyou
python main.py
```

## Building Executables

Each tool includes a build script or spec file for creating standalone executables:

```bash
# Build OCRTool (requires Tesseract in tesseract/ folder)
cd OCRTool
build.bat

# Build Speech to Text
cd Speech_to_text
build.bat

# Build Typer
cd Typer
pyinstaller Typer.spec

# Build Rockyou
cd Rockyou
build.bat
``'