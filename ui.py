import os
import tkinter as tk

from PIL import Image, ImageTk

FACES_DIR = "faces"
DISPLAY_SIZE = (800, 480)  # idle/ frames' native size; speaking/ frames get scaled to match

VISEME_FILES = {
    "closed": "speaking/speaking_01.png",
    "tiny": "speaking/speaking_02.png",
    "oh": "speaking/speaking_05.png",
    "wide": "speaking/speaking_03.png",
    "ah": "speaking/speaking_06.png",
}


class FaceUI:
    def __init__(self, master):
        self.master = master
        master.title("BMO")
        master.configure(bg="black")
        self.label = tk.Label(master, bg="black", borderwidth=0)
        self.label.pack()

        self.closed = False
        master.protocol("WM_DELETE_WINDOW", self._on_close)
        master.bind("<Escape>", lambda event: self._on_close())

        self._current_key = None  # None means "idle"

        self._idle_frames = self._load_frames("idle")
        self._idle_idx = 0

        self._viseme_images = {
            key: Image.open(os.path.join(FACES_DIR, path)).convert("RGB").resize(DISPLAY_SIZE, Image.LANCZOS)
            for key, path in VISEME_FILES.items()
        }
        self._photo_cache = {}
        self._precompute_blends()

        self._animate()

    def _precompute_blends(self):
        # render every base viseme + every ordered transition pair up front
        # so speak() never pays PIL blend / PhotoImage cost mid-timeline,
        # which was adding to the audio/animation drift
        keys = list(self._viseme_images)
        for key in keys:
            self._get_photo(key)
        for a in keys:
            for b in keys:
                if a != b:
                    self._get_photo(f"{a}->{b}")

    def _load_frames(self, state):
        path = os.path.join(FACES_DIR, state)
        files = sorted(f for f in os.listdir(path) if f.lower().endswith(".png"))
        return [
            ImageTk.PhotoImage(Image.open(os.path.join(path, f)).resize(DISPLAY_SIZE, Image.LANCZOS))
            for f in files
        ]

    def _get_photo(self, key):
        photo = self._photo_cache.get(key)
        if photo is not None:
            return photo

        if key in self._viseme_images:
            image = self._viseme_images[key]
        else:
            a, b = key.split("->")
            image = Image.blend(self._viseme_images[a], self._viseme_images[b], 0.5)

        photo = ImageTk.PhotoImage(image)
        self._photo_cache[key] = photo
        return photo

    def _on_close(self):
        # deliberately don't destroy() here -- the main loop still needs to
        # pump() a few more times before it notices `closed` and exits, and
        # a destroyed root would make those calls raise TclError
        self.closed = True

    def set_viseme(self, key):
        # update the displayed image immediately -- don't wait for the next
        # independent _animate() tick, since viseme segments (as short as
        # ~15-40ms) are often shorter than that tick interval and would
        # otherwise get silently dropped, making the mouth lag behind speech
        self._current_key = key
        self.label.config(image=self._get_photo(key))

    def clear_viseme(self):
        self._current_key = None

    def pump(self):
        """Process pending Tk events. Call frequently from the main loop
        (including while speak() is sleeping through a viseme timeline) so
        the window stays responsive and repaints."""
        self.master.update()

    def _animate(self):
        # only handles idle cycling -- set_viseme() updates the display
        # directly while speaking
        if self._current_key is None:
            frames = self._idle_frames
            self._idle_idx = (self._idle_idx + 1) % len(frames)
            self.label.config(image=frames[self._idle_idx])

        self.master.after(33, self._animate)
