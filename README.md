# project-bmo

A terminal chatbot that classifies user input into intents (defined in `intents.json`) using a small Keras neural net, then replies with a matching canned response.

## Requirements

- Python 3.10 (see `.python-version`)
- Dependencies in `requirements.txt`

## Setup

Using conda:

```
conda create -n project-bmo python=3.10 -y
conda activate project-bmo
pip install -r requirements.txt
```

Or with venv:

```
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then download the required NLTK data (one-time):

```
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('wordnet'); nltk.download('omw-1.4')"
```

## Training

Edit `intents.json` to add/change tags, patterns, and responses, then run:

```
python training.py
```

This writes `model/words.pkl`, `model/classes.pkl`, and `model/chatbotmodel.h5`. Re-run this any time `intents.json` changes.

## Voice (text-to-speech)

BMO speaks its replies aloud using [Piper](https://github.com/rhasspy/piper) with a custom BMO voice model (shared from the `be-more-hailo` project). Copy the voice files into place before running:

```
mkdir -p voice
cp ../be-more-hailo/piper/bmo.onnx ../be-more-hailo/piper/bmo.onnx.json voice/
```

Playback uses `sounddevice` (PortAudio).

### Voice cache

Since `intents.json`'s responses are a fixed, known set, run this once (and again any time responses change) to pre-synthesize them all:

```
python precompute_voice.py
```

This bakes each response's audio and exact viseme timeline into `voice_cache/` (~20x faster than live synthesis, measured). `speak()` checks this cache first and only falls back to live Piper synthesis for text that isn't cached — currently just the dynamic `time` response, which is different every call.

## Face UI + lip sync

`ui.py` opens a Tkinter window showing BMO's face (frames in `faces/`, generated from `svg_faces/`). While BMO is speaking, its mouth is driven by `viseme.py`, which classifies each phoneme Piper produces into one of 6 mouth shapes (closed / tiny / small / oh / wide / ah — `faces/speaking/speaking_0{1-6}.png`) and distributes the real audio duration across them. When the mouth shape changes, a blended in-between frame is shown briefly first instead of a hard cut, so the transition reads more like actual talking.

Piper doesn't expose true per-phoneme timing for this voice model, so the timing is a heuristic approximation (vowels held longer than consonants) rather than exact — good enough to look like talking, not frame-perfect lip sync.

## Running

```
python bmo.py
```

The face window opens and the chat prompt (`>`) runs in the terminal — type a message, BMO prints its reply, speaks it out loud, and its mouth animates in sync. Press `Esc` in the face window to stop.

Speech-to-text (talking to BMO instead of typing) is not implemented yet.

### Puppet mode

```
python bmo.py --as-bmo
```

Skips the intent classifier entirely — whatever you type is spoken directly as BMO (with lip sync), instead of BMO replying to you. Useful for making BMO say arbitrary lines on demand.
