import hashlib
import json
import os
import re
import time
import wave

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from viseme import build_timeline

VOICE_MODEL = "voice/bmo.onnx"
VOICE_CONFIG = "voice/bmo.onnx.json"
VOLUME = 0.75

CACHE_DIR = "voice_cache"

# sd.play() consistently takes ~140ms of internal buffering before the first
# sample is actually audible (measured empirically, stable across repeated
# calls) -- wait this long before starting the mouth timeline so it doesn't
# get a head start on the audio
PREROLL_SECONDS = 0.14

# words piper would otherwise sound out letter-by-letter or mispronounce
PRONUNCIATIONS = {
    "bmo": "beemo",
}

_voice = PiperVoice.load(VOICE_MODEL, config_path=VOICE_CONFIG)


def clean_text_for_speech(text: str) -> str:
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = text.replace('*', '')
    for word, replacement in PRONUNCIATIONS.items():
        text = re.sub(r'\b' + re.escape(word) + r'\b', replacement, text, flags=re.IGNORECASE)
    return text.strip()


def cache_key(clean_text: str) -> str:
    return hashlib.sha1(clean_text.encode()).hexdigest()[:16]


def cache_paths(clean_text: str):
    key = cache_key(clean_text)
    return (
        os.path.join(CACHE_DIR, f"{key}.wav"),
        os.path.join(CACHE_DIR, f"{key}.json"),
    )


def synthesize(clean_text: str):
    """Run BMO's voice model on clean_text. Returns (audio_float32, sample_rate, timeline)
    where timeline is a flat list of (viseme_key, duration_seconds) segments."""
    chunks = list(_voice.synthesize(clean_text, include_alignments=True))
    if not chunks:
        return None

    audio = np.concatenate([c.audio_float_array for c in chunks]).astype(np.float32)
    sample_rate = chunks[0].sample_rate
    timeline = []
    for chunk in chunks:
        duration = len(chunk.audio_float_array) / chunk.sample_rate
        timeline.extend(build_timeline(chunk.phonemes, duration))
    return audio, sample_rate, timeline


def save_to_cache(clean_text: str, audio: np.ndarray, sample_rate: int, timeline: list):
    os.makedirs(CACHE_DIR, exist_ok=True)
    wav_path, meta_path = cache_paths(clean_text)

    audio_i16 = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(wav_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_i16.tobytes())

    with open(meta_path, 'w') as f:
        json.dump({"text": clean_text, "sample_rate": sample_rate, "timeline": timeline}, f, indent=2)


def load_from_cache(clean_text: str):
    wav_path, meta_path = cache_paths(clean_text)
    if not (os.path.exists(wav_path) and os.path.exists(meta_path)):
        return None

    with open(meta_path) as f:
        meta = json.load(f)
    with wave.open(wav_path, 'rb') as wf:
        raw = wf.readframes(wf.getnframes())
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return audio, meta["sample_rate"], meta["timeline"]


def _sleep_and_pump(ui, duration):
    # keep the Tk window responsive/repainting during long segments instead
    # of blocking it for the full duration
    end = time.monotonic() + duration
    while True:
        if ui.closed:
            return
        ui.pump()
        # recompute remaining *after* pump() so its cost doesn't silently
        # add to this segment's overshoot
        remaining = end - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(0.015, remaining))


def speak(text: str, ui=None):
    clean_text = clean_text_for_speech(text)
    if not clean_text or not any(c.isalnum() for c in clean_text):
        return

    # skip Piper synthesis entirely for lines already baked by
    # precompute_voice.py (every canned response in intents.json)
    result = load_from_cache(clean_text) or synthesize(clean_text)
    if result is None:
        return
    audio, sample_rate, timeline = result

    # playing straight from the array via sounddevice/PortAudio keeps audio
    # inside this process (reusing an already-open output stream when
    # possible) instead of spawning a fresh afplay process per utterance,
    # which was the dominant source of startup lag between audio and mouth
    sd.play(audio * VOLUME, samplerate=sample_rate)

    if ui is not None:
        time.sleep(PREROLL_SECONDS)
        for viseme_key, seg_duration in timeline:
            if ui.closed:
                break
            ui.set_viseme(viseme_key)
            _sleep_and_pump(ui, seg_duration)

        if ui.closed:
            sd.stop()
        else:
            ui.clear_viseme()
            ui.pump()

    sd.wait()
