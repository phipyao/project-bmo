# Piper's bmo.onnx model doesn't expose real per-phoneme durations
# (AudioChunk.phoneme_id_samples is None for this voice), so exact timing
# isn't available. Instead we classify each phoneme into one of the 6
# mouth shapes BMO already has (faces/speaking/speaking_0{1-6}.png) and
# distribute the *actual* audio duration across them using rough duration
# weights (vowels held longer than consonants) -- an approximation, but one
# driven by the real phoneme sequence rather than just amplitude.

# IPA modifiers that don't get their own mouth frame -- they just lengthen
# whichever real phoneme they're attached to (stress/length marks).
_MODIFIERS = {"ˈ", "ˌ", "ː", "ˑ", "ʲ", "ʷ", "̃", "̩"}

# Bilabial closures -- lips fully shut.
_CLOSED_CONSONANTS = {"p", "b", "m"}

_PAUSE_TOKENS = {" ", "!", ".", "?", ",", ";", ":"}

# Vowel -> mouth-shape mapping (espeak-ng IPA symbols).
_VOWEL_VISEME = {
    # rounded / back -> tall round "oh" mouth
    "o": "oh", "oʊ": "oh", "u": "oh", "uː": "oh", "ʊ": "oh", "ɔ": "oh", "ɔɪ": "oh", "w": "oh",
    # open / low, mid, and high-front vowels all share the "wide" open-mouth
    # frame -- speaking_04 (formerly used for these) reads as a barely-open
    # teeth shape rather than an open mouth, so every vowel that landed there
    # looked like BMO wasn't opening its mouth. Better to have all non-round
    # vowels visibly open (even if it loses some fine-grained distinction)
    # than to have common vowels (schwa especially) look closed.
    "æ": "wide", "ʌ": "wide", "ɑ": "wide", "a": "wide", "aʊ": "wide",
    "ə": "wide", "ɛ": "wide", "e": "wide", "eɪ": "wide", "ɚ": "wide", "ɜ": "wide",
    "i": "wide", "iː": "wide", "ɪ": "wide", "j": "wide", "y": "wide",
    # low diphthong -> big grin-open mouth
    "aɪ": "ah",
}

_VOWEL_MS = 130
_CONSONANT_MS = 70
_PAUSE_MS = 110
_MIN_MS = 40

_MAX_BLEND_MS = 40


def _classify(phoneme: str) -> str:
    if phoneme in _PAUSE_TOKENS or phoneme in _CLOSED_CONSONANTS:
        return "closed"
    if phoneme in _VOWEL_VISEME:
        return _VOWEL_VISEME[phoneme]
    return "tiny"  # default mouth-partly-open consonant shape


def _merge_diphthongs(phonemes: list) -> list:
    # Piper emits diphthongs as two separate single-char phonemes (e.g. "a",
    # "ɪ") rather than the combined "aɪ" token, so the multi-char keys in
    # _VOWEL_VISEME (aɪ/oʊ/ɔɪ/aʊ/eɪ) would otherwise never match. Glue
    # adjacent pairs back together here so the intended diphthong viseme
    # (e.g. "ah" for aɪ, not "wide" from "a" alone) actually gets used.
    merged = []
    i = 0
    while i < len(phonemes):
        if i + 1 < len(phonemes):
            pair = phonemes[i] + phonemes[i + 1]
            if pair in _VOWEL_VISEME:
                merged.append(pair)
                i += 2
                continue
        merged.append(phonemes[i])
        i += 1
    return merged


def build_timeline(phonemes: list, audio_seconds: float) -> list:
    """Turn a phoneme sequence + known audio duration into a list of
    (viseme_key, duration_seconds) segments. Consecutive segments that
    change mouth shape get a short blended "a->b" transition segment
    inserted between them instead of a hard cut."""
    phonemes = _merge_diphthongs(phonemes)
    segments = []  # (viseme, weight_ms)
    for ph in phonemes:
        if ph in _MODIFIERS:
            if segments:
                v, w = segments[-1]
                segments[-1] = (v, w * 1.4)  # lengthen instead of new frame
            continue
        viseme = _classify(ph)
        is_open_vowel = viseme not in ("tiny", "closed")
        weight = _PAUSE_MS if ph in _PAUSE_TOKENS else (_VOWEL_MS if is_open_vowel else _CONSONANT_MS)
        segments.append((viseme, max(weight, _MIN_MS)))

    if not segments:
        return [("closed", audio_seconds)]

    total_weight = sum(w for _, w in segments)
    scale = (audio_seconds * 1000) / total_weight if total_weight else 1.0

    timeline = []
    prev_viseme = None
    for viseme, weight in segments:
        duration = (weight * scale) / 1000
        if prev_viseme is not None and viseme != prev_viseme:
            blend_dur = min(_MAX_BLEND_MS / 1000, duration * 0.3)
            timeline.append((f"{prev_viseme}->{viseme}", blend_dur))
            duration -= blend_dur
        if duration > 0:
            timeline.append((viseme, duration))
        prev_viseme = viseme
    return timeline
