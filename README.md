# Live Translation

A macOS app that captures any audio playing on your Mac — YouTube, Zoom, Twitch, livestreams, or any other app — transcribes it, translates it, and displays the original and translation side by side in a floating glass overlay.

Everything runs locally on Apple silicon. No API keys, accounts, or cloud services are required, and your audio never leaves the Mac.

<p align="center">
  <img src="docs/screenshot.png" alt="Live Translation overlay — original on the left, translation on the right" width="700">
</p>

## TL;DR

```text
system audio ──► Whisper ──► glass overlay
   BlackHole       MLX         PyObjC

         ──► Whisper translate ──►  (no Ollama required)
         ──► Whisper + Ollama  ──►  (higher quality, more languages)
```

- MLX Whisper for transcription (and optionally translation)
- Gemma 4 through Ollama for translation (optional — Ollama-free mode available)
- Silero VAD for speech detection
- PyObjC for the always-on-top overlay

## Who is this for?

- You watch foreign-language media — films, series, news, YouTube, Twitch, documentaries — and want live captions + translation instead of waiting for subtitles.
- You're learning a language and want the original and translation side by side on real speech.
- You sit in calls/meetings in a language you only half-speak.
- You need captions and translation for accessibility on audio that has none.
- You want it fully offline and private.

## How it is different

Most similar projects are cloud-based, transcription-only, file-based, tied to a meeting platform, or designed for OBS.

Live Translation combines:

- system-wide audio capture;
- real-time transcription;
- sentence-level LLM translation;
- a floating bilingual overlay;
- local processing;
- segmentation designed to avoid losing or repeating words.

## Quickstart

Requires macOS with Apple silicon.

```bash
git clone https://github.com/KazKozDev/live-translation.git
cd live-translation
./setup.sh
```

Or install manually:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
brew bundle --file=Brewfile
```

Use `requirements.lock.txt` if you need the exact pinned environment.

### Route system audio through BlackHole

macOS does not allow ordinary apps to capture system output directly, so Live Translation uses BlackHole 2ch.

To keep hearing audio while capturing it:

1. Open Audio MIDI Setup
2. Click **+** → **Create Multi-Output Device**
3. Enable your normal output and *BlackHole 2ch*
4. Select the Multi-Output Device in System Settings → Sound → Output

The first launch may request microphone permission. This is required to read BlackHole audio.

### Models

#### Whisper

Supported MLX Whisper models:

- `small` — lowest resource usage
- `medium` — balanced; translate-capable
- `turbo` — fastest, but **transcribe-only** (cannot translate)
- `large-q4` — 4-bit large-v3 (~1.6GB); translate-capable, default for `--whisper-translate`
- `large` — highest accuracy; translate-capable

> `turbo` (large-v3-turbo) is a distilled, transcribe-only model. With `--whisper-translate` it returns source-language text instead of English, so the app auto-swaps it to `large-q4` and prints a warning.

Pre-download the default models:

```bash
./.venv/bin/python -c "from huggingface_hub import snapshot_download; \
[snapshot_download(r) for r in (
  'mlx-community/whisper-medium-mlx',
  'mlx-community/whisper-large-v3-turbo',
  'mlx-community/whisper-large-v3-mlx-4bit'
)]"
```

#### Gemma 4 (optional — only needed for non-English targets or higher translation quality)

Supported Ollama models:

```text
gemma4:12b-mlx   (~7GB)   — recommended
gemma4:e4b-mlx   (~2.5GB) — lightest
gemma4:26b-mlx   (~16GB)  — highest quality; requires 18GB+ unified memory
```

Download with:

```bash
ollama pull gemma4:12b-mlx
```

If you only need Ukrainian → English, use `--whisper-translate` and skip Ollama entirely.

Recommended preset (UK→EN, no Ollama): **Whisper `large-q4` + `--whisper-translate`** (~1.6GB)
Recommended preset (with Ollama): **Whisper Turbo + Gemma 4 12B** (~8.5GB total)

### Run

Launch `LiveTranslate.app`, or run:

```bash
./.venv/bin/python live_translate_overlay.py --target ru
```

#### Ollama-free mode (Ukrainian → English, no LLM needed)

Whisper has a built-in translate task that outputs English directly from any source language.
No Ollama, no Gemma, no extra download beyond the Whisper model itself.

```bash
./.venv/bin/python live_translate_overlay.py --whisper-translate --source uk
```

Defaults to `large-q4` (translate-capable). The overlay shows a single full-width English column in this mode. Use `--whisper medium` for faster captions, or `--whisper large` for highest accuracy. `turbo` is rejected for translation (auto-swapped to `large-q4`).

#### With Ollama (any target language)

```bash
# Start Ollama in another terminal
ollama serve

# Translate to any language
./.venv/bin/python live_translate_overlay.py \
    --source uk \
    --target en \
    --ollama-model gemma4:12b-mlx
```

Example with fixed languages and a different Whisper model:

```bash
./.venv/bin/python live_translate_overlay.py \
    --source es \
    --target en \
    --whisper large \
    --ollama-model gemma4:12b-mlx
```

### Batch transcribe a video file

After a recording (from OBS or anywhere), use `transcribe_file.py` to get subtitles:

```bash
# Translate Ukrainian video to English SRT (uses large model for best quality):
./.venv/bin/python transcribe_file.py video.mp4 --task translate --whisper large

# Fast pass with turbo:
./.venv/bin/python transcribe_file.py video.mp4 --task translate --whisper turbo

# Keep original language (no translation):
./.venv/bin/python transcribe_file.py video.mp4 --task transcribe --whisper large

# Choose output format (srt/vtt/txt):
./.venv/bin/python transcribe_file.py video.mp4 --task translate --format vtt -o subs.vtt
```

The script accepts any format ffmpeg can read — `.mp4`, `.mkv`, `.mov`, `.mp3`, `.wav`, etc.
Output defaults to the same filename with the new extension next to the input file.

### Install the app

```bash
./install-app.sh
```

Or choose another destination:

```bash
./install-app.sh ~/Apps
```

The app is ad-hoc signed. On first launch, right-click it and select **Open**.

## How it works

### Lossless segmentation

Fixed five-second chunks often make Whisper cut words, repeat phrases, or add false punctuation.

The default pipeline instead:

1. detects speech and pauses with Silero VAD;
2. creates overlapping speech segments;
3. removes duplicated text at segment boundaries;
4. fixes punctuation introduced by artificial pauses;
5. rebuilds complete sentences;
6. sends those sentences to the translation model.

Under normal load, the queue catches up instead of dropping speech. During severe overload, stale audio may be skipped to return to live output.

### Streaming mode

Enable it with `--streaming`. Streaming re-transcribes a rolling buffer and commits words after two consecutive passes agree. Use `--show-partial` to see the unconfirmed tail and `--update-seconds 1.5` to control re-transcription frequency.

It produces smoother partial captions but uses more compute and may lose content under load, so it is disabled by default.

### Hallucination reduction

Silero VAD removes silence and non-speech before transcription. The pipeline also filters common false outputs such as "thanks for watching", "subtitles by amara.org", and similar phrases. This reduces hallucinations but does not eliminate them completely.

### Sentence-level translation

The LLM receives complete sentences plus recent context, producing more coherent translations than word-by-word machine translation.

## Main options

```text
--source LANGUAGE
--target LANGUAGE
--whisper MODEL            small | medium | turbo | large-q4 | large
--whisper-translate        use Whisper's built-in translation; no Ollama needed (turbo not supported)
--ollama-model MODEL
--silence-rms VALUE
--vad-min-speech-ms VALUE
--audio-queue SIZE
--show-partial
--streaming
--update-seconds VALUE
```

View all options:

```bash
./.venv/bin/python live_translate_overlay.py --help
```

## Limitations

- macOS and Apple silicon only
- BlackHole setup is required
- larger models increase latency and memory usage
- automatic language detection can be unstable with mixed-language audio
- streaming mode is more compute-demanding
- Whisper can still hallucinate occasionally

## Project structure

```text
live_translate_overlay.py   CLI, audio pipeline, and Cocoa overlay
transcribe_file.py          batch transcribe/translate a video or audio file
live_translation/           segmentation, cleanup, and translation
LiveTranslate.app           macOS app bundle
install-app.sh              app installer
setup.sh / Brewfile         setup files
requirements*.txt           dependencies
tests/                      unit tests
```

## Development

```bash
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/python -m ruff check .
./.venv/bin/python -m pyright
./.venv/bin/python -m pytest
```

## License

[MIT](LICENSE) — use, modify, and redistribute freely.

## Acknowledgements

Thanks to [Alex Ziskind](https://github.com/alexziskind1) for the [benchmark](https://www.youtube.com/watch?v=PxUSE2KwyUQ) that pointed to the MLX Whisper path.
