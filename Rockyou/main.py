"""
Keyboard/Mouse Calibration & Replay Tool
-----------------------------------------
1. Press Esc to start recording keyboard/mouse actions
2. Press Esc again to stop recording
3. Loops through rockyou.txt: types each password, replays recorded sequence
4. Press Esc during loop to kill
"""

import sys
import os
import time
import threading
from pynput import keyboard, mouse


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    else:
        # Running as script
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
import pyautogui

# Global state
recorded_events = []
is_recording = False
recording_start_time = None
running = True
keyboard_controller = KeyboardController()
mouse_controller = MouseController()


def countdown(seconds, message):
    """Display a countdown timer."""
    print(f"\n{message}")
    for i in range(seconds, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    print("  GO!\n")


def start_calibration():
    """Wait for Esc, countdown, then record actions until Esc is pressed again."""
    global recorded_events, is_recording, recording_start_time
    
    print("\n" + "=" * 50)
    print("CALIBRATION MODE")
    print("=" * 50)
    print("Press [Esc] to start recording...")
    
    # Wait for Esc to start
    start_event = threading.Event()
    
    def wait_for_start(key):
        if key == Key.esc:
            start_event.set()
            return False
    
    with keyboard.Listener(on_press=wait_for_start) as listener:
        listener.join()
    
    countdown(3, "Recording will start in:")
    
    # Start recording
    recorded_events = []
    is_recording = True
    recording_start_time = time.time()
    
    print("🔴 RECORDING! Perform your actions now...")
    print("Press [Esc] to STOP recording.\n")
    
    stop_event = threading.Event()
    
    def on_key_press(key):
        global is_recording
        if key == Key.esc:
            is_recording = False
            stop_event.set()
            return False
        
        if is_recording:
            recorded_events.append({
                'type': 'key_press',
                'key': key,
                'time': time.time() - recording_start_time
            })
    
    def on_key_release(key):
        if key == Key.esc:
            return
        
        if is_recording:
            recorded_events.append({
                'type': 'key_release',
                'key': key,
                'time': time.time() - recording_start_time
            })
    
    def on_mouse_click(x, y, button, pressed):
        if is_recording:
            recorded_events.append({
                'type': 'mouse_click',
                'x': x,
                'y': y,
                'button': button,
                'pressed': pressed,
                'time': time.time() - recording_start_time
            })
    
    def on_mouse_move(x, y):
        if is_recording:
            # Only record significant movements to avoid flooding
            if len(recorded_events) == 0 or recorded_events[-1].get('type') != 'mouse_move':
                recorded_events.append({
                    'type': 'mouse_move',
                    'x': x,
                    'y': y,
                    'time': time.time() - recording_start_time
                })
            else:
                # Update the last move event
                recorded_events[-1]['x'] = x
                recorded_events[-1]['y'] = y
                recorded_events[-1]['time'] = time.time() - recording_start_time
    
    # Start listeners
    keyboard_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
    mouse_listener = mouse.Listener(on_click=on_mouse_click, on_move=on_mouse_move)
    
    keyboard_listener.start()
    mouse_listener.start()
    
    # Wait for stop
    stop_event.wait()
    
    keyboard_listener.stop()
    mouse_listener.stop()
    
    # Sort events by time
    recorded_events.sort(key=lambda e: e['time'])
    
    print(f"\n✓ Recording stopped! Captured {len(recorded_events)} events.")
    return recorded_events


def replay_sequence():
    """Replay the recorded keyboard/mouse sequence as fast as possible."""
    if not recorded_events:
        return
    
    for event in recorded_events:
        # Check if we should stop
        if not running:
            return
        
        # Replay the event immediately (no delay)
        if event['type'] == 'key_press':
            try:
                keyboard_controller.press(event['key'])
            except Exception:
                pass
                
        elif event['type'] == 'key_release':
            try:
                keyboard_controller.release(event['key'])
            except Exception:
                pass
                
        elif event['type'] == 'mouse_move':
            mouse_controller.position = (event['x'], event['y'])
            
        elif event['type'] == 'mouse_click':
            mouse_controller.position = (event['x'], event['y'])
            if event['pressed']:
                mouse_controller.press(event['button'])
            else:
                mouse_controller.release(event['button'])


def type_password(password):
    """Type a password using pyautogui."""
    try:
        pyautogui.write(password, interval=0.02)
    except Exception as e:
        # Some characters might not be typeable
        print(f"  Warning: Could not type some characters: {e}")


def setup_kill_listener():
    """Set up a background listener for Esc to kill the loop."""
    global running
    
    def on_press(key):
        global running
        if key == Key.esc:
            running = False
            print("\n\n🛑 ESC pressed - Stopping...")
            return False
    
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    return listener


def main():
    """Main program flow."""
    global running
    
    print("\n" + "=" * 50)
    print("  ROCKYOU PASSWORD REPLAY TOOL")
    print("=" * 50)
    print("\nThis tool will:")
    print("  1. Record your keyboard/mouse actions")
    print("  2. Loop through rockyou.txt passwords")
    print("  3. Type each password + replay your actions")
    print("\nPress ESC to start/stop recording and to kill the loop.\n")
    
    # Step 1: Record calibration sequence
    start_calibration()
    
    if not recorded_events:
        print("\n⚠ No events recorded. Exiting.")
        return
    
    # Step 2: Start the kill listener
    kill_listener = setup_kill_listener()
    
    # Step 3: Main loop
    print("\n" + "=" * 50)
    print("STARTING PASSWORD LOOP")
    print("=" * 50)
    print("Press ESC to stop at any time.\n")
    
    countdown(3, "Starting in:")
    
    rockyou_path = get_resource_path('rockyou.txt')
    
    try:
        with open(rockyou_path, 'r', encoding='utf-8', errors='replace') as f:
            line_num = 0
            for line in f:
                if not running:
                    break
                
                password = line.strip()
                if not password:
                    continue
                
                line_num += 1
                print(f"[{line_num}] Trying: {password[:20]}{'...' if len(password) > 20 else ''}")
                
                # Type the password
                type_password(password)
                
                # Replay the recorded sequence
                replay_sequence()
                
                if not running:
                    break
                
                # Wait between attempts
                time.sleep(0.05)
                
    except FileNotFoundError:
        print("❌ Error: rockyou.txt not found in current directory!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        running = False
        kill_listener.stop()
    
    print("\n" + "=" * 50)
    print("Program ended.")
    print("=" * 50)


if __name__ == "__main__":
    main()
