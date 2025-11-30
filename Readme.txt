# 🎤 Live Malayalam → Arabic Speech Translator
**Keralolsavam 2025 (Dubai) — Stage demo**

A real-time Malayalam → Arabic speech translation demo. The browser captures microphone audio, slices it into short WAV chunks, and POSTs each chunk to a Flask backend (`/transcribe`). The backend performs speech-to-text (Malayalam) and translates the text to Arabic, returning JSON that the frontend displays in a projector-friendly UI.

---

## 🚀 Project summary (one-paragraph)
This project captures live Malayalam speech from the browser, sends short WAV chunks to a Flask server, uses Google Cloud Speech-to-Text to transcribe Malayalam, then translates the transcription to Arabic (Google Translate API). The frontend shows both Malayalam and Arabic text live, includes a mic-level meter and history panel, and is tuned for low-latency stage use. Optional TTS can be added to play Arabic audio.

---

## 📦 All required tools & packages (to include in repo README)

### System / tools (install these first)
- **Python 3.10+** (3.11 recommended)
- **git** (for source control / pushing to GitHub)
- **ffmpeg** (for any mp3/webm → WAV conversions)
  - Ubuntu/Debian: `sudo apt update && sudo apt install ffmpeg`
  - macOS (Homebrew): `brew install ffmpeg`
  - Windows: download from https://ffmpeg.org and add to `PATH`
- (Optional) **Docker** (if you want containerized deployment)

### Python packages (put these in `requirements.txt`)
Use the following `requirements.txt` (example). Add or remove packages depending on your final implementation.

