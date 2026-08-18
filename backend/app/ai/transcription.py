import os
import time
from google import genai


def transcribe_audio(audio_path):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)

    uploaded_file = client.files.upload(file=audio_path)

    prompt = """
Generate an accurate transcript of the speech in this audio.

Return ONLY the transcript.
Do not add commentary, summaries, labels, markdown, or explanations.
"""

    # Try multiple Gemini models if one is temporarily unavailable.
    models = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
    ]

    last_error = None

    for model in models:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[prompt, uploaded_file],
                )

                text = (response.text or "").strip()

                if text:
                    return {
                        "text": text,
                        "words": []
                    }

            except Exception as exc:
                last_error = exc

                # Retry temporary 503/429 errors.
                error_text = str(exc)

                if "503" in error_text or "UNAVAILABLE" in error_text:
                    time.sleep(2 ** attempt)
                    continue

                if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                    time.sleep(2 ** attempt)
                    continue

                raise

    raise RuntimeError(
        f"Gemini transcription failed after retries: {last_error}"
    )