"""Pre-synthesize every canned response in intents.json to voice_cache/ so
speak() can skip live Piper synthesis for them at chat time. Re-run this any
time intents.json's responses change.
"""

import json

import tts


def main():
    with open("intents.json") as f:
        intents = json.load(f)

    cached, skipped = 0, 0
    for intent in intents["intents"]:
        for response in intent.get("responses", []):
            clean_text = tts.clean_text_for_speech(response)
            if not clean_text or not any(c.isalnum() for c in clean_text):
                continue

            wav_path, meta_path = tts.cache_paths(clean_text)
            if tts.load_from_cache(clean_text) is not None:
                skipped += 1
                print(f"  [{intent['tag']}] {response!r} -> already cached")
                continue

            result = tts.synthesize(clean_text)
            if result is None:
                continue
            audio, sample_rate, timeline = result
            tts.save_to_cache(clean_text, audio, sample_rate, timeline)
            cached += 1
            print(f"  [{intent['tag']}] {response!r} -> {wav_path}")

    print(f"\nCached {cached} new responses, {skipped} already up to date, in {tts.CACHE_DIR}/")


if __name__ == "__main__":
    main()
