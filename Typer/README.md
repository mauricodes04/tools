# Typer

A simple GUI tool to automatically type text into another window (e.g., VirtualBox, remote desktop sessions, or any application that doesn't support copy/paste).

## Features

- **GUI Interface** - Easy-to-use window to paste your text/code
- **Configurable Typing Delay** - Adjust the speed of typing (seconds per character)
- **Countdown Timer** - 5-second countdown to switch to your target window
- **Auto-Minimize** - Optionally minimizes during countdown so keystrokes don't land in the wrong window
- **Cancel Support** - Cancel the operation at any time

## Use Cases

- Typing into VirtualBox VMs that don't have Guest Additions installed
- Entering code/text into sandboxed or restricted environments
- Bypassing paste restrictions in certain applications
- Automating text entry in legacy systems

## Installation

### From Source

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/Typer.git
   cd Typer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python typer2.py
   ```

### Pre-built Executable

Download `Typer.exe` from the [Releases](https://github.com/yourusername/Typer/releases) page - no Python installation required.

## Usage

1. Launch Typer
2. Paste your text/code into the text area
3. Adjust the typing delay if needed (default: 0.05 seconds per character)
4. Click **Type**
5. Quickly click into your target window (VirtualBox, etc.) during the 5-second countdown
6. Watch as Typer automatically types your text

## Building the Executable

To build a standalone `.exe` file:

```bash
pip install pyinstaller
pyinstaller Typer.spec
```

The executable will be created in the `dist/` folder.

## Requirements

- Python 3.6+
- pyautogui

## License

MIT License
