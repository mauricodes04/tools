# Rockyou Password Replay Tool

A keyboard/mouse calibration and replay tool that records your input actions and replays them with passwords from a wordlist.

This tool is intended for **authorized security testing and educational purposes only**. Only use this tool on systems you own or have explicit permission to test.

### Setup

#### Install rockyou.txt

The `rockyou.txt` wordlist is required but not included in this repository. To obtain it:

1. **From Kali Linux**: The file is pre-installed at `/usr/share/wordlists/rockyou.txt.gz`
   ```bash
   gunzip /usr/share/wordlists/rockyou.txt.gz
   cp /usr/share/wordlists/rockyou.txt .
   ```

2. **Download from GitHub**:
   ```bash
   curl -L -o rockyou.txt https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt
   ```

3. **Manual download**: Search for "rockyou.txt download" and place the file in the `Rockyou/` directory.


### Run
   ```bash
   python main.py
   ```

### Build Executable
   ```bash
   build.bat
   ```
Find the executable in `dist/Rockyou/Rockyou.exe`
