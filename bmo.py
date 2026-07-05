import argparse
import select
import sys
import time
import tkinter as tk

from inference import chat
from tts import speak
from ui import FaceUI


def _input_ready():
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    return bool(ready)


def parse_args():
    parser = argparse.ArgumentParser(description="BMO terminal chatbot")
    parser.add_argument(
        "--as-bmo",
        action="store_true",
        help="Speak whatever you type directly as BMO (no intent classifier), instead of chatting with BMO.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    root = tk.Tk()
    ui = FaceUI(root)

    if args.as_bmo:
        print("as-bmo mode -- type anything and BMO will say it")
    else:
        print("bmo is up!")
        print("use /bmo <text> to make BMO say something directly")
    print("press esc in the face window to quit")
    print("> ", end="", flush=True)
    while not ui.closed:
        if _input_ready():
            line = sys.stdin.readline()
            if not line:  # EOF
                break
            msg = line.rstrip("\n")
            if args.as_bmo:
                speak(msg, ui=ui)
            elif msg.startswith("/bmo "):
                speak(msg[len("/bmo "):], ui=ui)
            else:
                response = chat(msg)
                print(response)
                speak(response, ui=ui)
            if ui.closed:
                break
            print("> ", end="", flush=True)
        else:
            ui.pump()
            time.sleep(0.01)

    if not ui.closed:
        root.destroy()
    print()
