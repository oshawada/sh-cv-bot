# tools/extract_job_info.py
# Purpose: Use Gemini Vision to extract job info from a screenshot
# Inputs: image bytes
# Outputs: dict {email, job_title, company, requirements_summary}

import os
import json
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

_FAST_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0)
)

load_dotenv()

_client = None


def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


def extract_job_info(image_bytes: bytes) -> dict:
    prompt = """You are reading a screenshot of a LinkedIn job post or any job advertisement.

Extract the following information and return ONLY valid JSON (no markdown, no explanation):
{
  "email": "the email address to apply to, or null if not found",
  "job_title": "the job title/position name",
  "company": "the company name, or null if not found",
  "requirements_summary": "a brief summary of the key job requirements and responsibilities in English"
}

If no email address is visible in the image, set email to null.
If you cannot determine a field, set it to null."""

    response = get_client().models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt,
        ],
        config=_FAST_CONFIG,
    )

    text = response.text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    return json.loads(text)


if __name__ == "__main__":
    with open("test_screenshot.jpg", "rb") as f:
        image_bytes = f.read()
    result = extract_job_info(image_bytes)
    print(json.dumps(result, indent=2, ensure_ascii=False))
