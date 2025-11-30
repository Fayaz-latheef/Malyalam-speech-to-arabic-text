# app.py
# Flask app to accept uploaded audio, transcribe with Google Speech, translate to Arabic,
# and return JSON. Robust logging + helpful errors for debugging.

import os
import tempfile
import traceback
import subprocess
from flask import Flask, request, jsonify, send_from_directory
from google.cloud import speech_v1 as speech
from google.cloud import translate_v2 as translate

app = Flask(__name__)

# Maximum upload size (optional)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25 MB

# Configure default languages
SOURCE_LANGUAGE = "ml-IN"   # Malayalam (India) - adjust if needed
TARGET_LANGUAGE = "ar"      # Arabic

# helper: run ffmpeg to convert input -> 16k mono WAV
def convert_to_wav(input_path, output_path):
    # ffmpeg -y -i input -ar 16000 -ac 1 output
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        output_path
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        # include stderr text to help debug ffmpeg issues
        stderr_text = proc.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"ffmpeg failed: rc={proc.returncode}\nstderr:\n{stderr_text}")
    return output_path

# helper: transcribe wav file using Google Cloud Speech
def transcribe_wav(wav_path, language_code=SOURCE_LANGUAGE):
    client = speech.SpeechClient()
    with open(wav_path, "rb") as f:
        content = f.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language_code,
        enable_automatic_punctuation=True,
        audio_channel_count=1,
    )

    response = client.recognize(config=config, audio=audio)
    # join all results
    transcripts = []
    for result in response.results:
        # choose the top alternative
        transcripts.append(result.alternatives[0].transcript)
    transcript_text = " ".join(transcripts).strip()
    return transcript_text

# helper: translate using Google Translate v2
def translate_text(text, target_language=TARGET_LANGUAGE):
    tclient = translate.Client()
    result = tclient.translate(text, target_language=target_language)
    # result contains 'translatedText'
    return result.get("translatedText")

@app.route("/")
def index():
    # serve the index.html from same folder (replace with your real frontend file if different)
    return send_from_directory(".", "index.html")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    """
    Accepts:
      - multipart/form-data with file field name 'audio' (or 'file', 'recordedFile'), OR
      - raw bytes in request.data (content-type could be application/octet-stream)
    Returns:
      - JSON with 'transcript' and 'translation' on success (200)
      - JSON with 'warning' when recognized speech is empty (200)
      - JSON with 'error' and 'traceback' on server error (500)
    """

    # Keep list of temporary files to cleanup
    tmp_files = []
    try:
        app.logger.info("Incoming /transcribe request: headers=%s", dict(request.headers))

        audio_file = None
        # common form names used by frontends
        for key in ("audio", "file", "recordedFile"):
            if key in request.files:
                audio_file = request.files[key]
                break

        if audio_file is None:
            # maybe frontend POSTed raw bytes (fetch arrayBuffer/body)
            if request.data and len(request.data) > 0:
                tmp_in = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
                tmp_in.write(request.data)
                tmp_in.flush()
                tmp_in.close()
                incoming_path = tmp_in.name
                tmp_files.append(incoming_path)
                app.logger.info("Saved raw request.data to %s", incoming_path)
            else:
                # No file at all
                msg = ("No audio file found in the request. "
                       "Form keys tried: audio,file,recordedFile. "
                       "If you use fetch() with form-data, ensure form field name is 'audio'. "
                       "If using raw bytes, ensure request.body contains audio.")
                app.logger.error(msg + " request.files keys=%s", list(request.files.keys()))
                return jsonify({"error": "no_audio", "message": msg, "files": list(request.files.keys())}), 400
        else:
            # save uploaded file to temp file
            suffix = os.path.splitext(audio_file.filename)[1] or ".webm"
            tmp_in = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            audio_file.save(tmp_in.name)
            incoming_path = tmp_in.name
            tmp_files.append(incoming_path)
            app.logger.info("Saved uploaded file %s to %s", audio_file.filename, incoming_path)

        # convert to 16k mono WAV (LINEAR16)
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = tmp_wav.name
        tmp_wav.close()
        tmp_files.append(wav_path)

        # run ffmpeg conversion (this can raise)
        try:
            convert_to_wav(incoming_path, wav_path)
            app.logger.info("Converted audio to wav: %s", wav_path)
        except Exception as e:
            # include ffmpeg stderr in returned error
            app.logger.error("ffmpeg conversion failed: %s", str(e))
            raise

        # transcribe
        transcript = transcribe_wav(wav_path)
        app.logger.info("Transcription result: %s", transcript)

        if not transcript:
            # return useful message rather than blank 200
            return jsonify({
                "transcript": "",
                "translation": "",
                "warning": "No speech recognized. Try speaking louder, check mic, or use a clearer audio format."
            }), 200

        # translate
        translation = translate_text(transcript, TARGET_LANGUAGE)
        app.logger.info("Translation result: %s", translation)

        # cleanup temp files
        for p in tmp_files:
            try:
                os.remove(p)
            except Exception:
                pass

        return jsonify({"transcript": transcript, "translation": translation}), 200

    except Exception as e:
        tb = traceback.format_exc()
        # print full traceback to server console for debugging
        app.logger.error("Exception in /transcribe: %s\n%s", e, tb)
        # return JSON with error and traceback (debug only; remove tb in production)
        return jsonify({"error": "internal_server_error", "exception": str(e), "traceback": tb}), 500
    finally:
        # ensure no stray temp files remain on unexpected exit
        try:
            for p in tmp_files:
                if os.path.exists(p):
                    os.remove(p)
        except Exception:
            pass

if __name__ == "__main__":
    # Helpful debug info on start
    print("GOOGLE_APPLICATION_CREDENTIALS:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    print("Ensure ffmpeg in PATH by running: ffmpeg -version")
    app.run(host="0.0.0.0", port=5000, debug=True)
