# tools/generate_email.py
# Purpose: Select the right CV and generate a cover letter based on CV content + job requirements
# Inputs: job_info dict, selected_cv (optional override)
# Outputs: dict {cv_path, cv_name, cv_filename, email_body, subject, confidence}

import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pypdf import PdfReader
from download_cvs import CV_FILES, get_all_cvs

load_dotenv()

_client = None
_cv_text_cache: dict = {}

_FAST_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0)
)


def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


def read_cv_text(cv_path: str) -> str:
    if cv_path not in _cv_text_cache:
        reader = PdfReader(cv_path)
        _cv_text_cache[cv_path] = "\n".join(
            page.extract_text() or "" for page in reader.pages
        ).strip()
    return _cv_text_cache[cv_path]


def select_cv(requirements_summary: str) -> tuple[dict, int]:
    """Returns (best_cv, confidence_score). Score 0 means uncertain."""
    text = requirements_summary.lower()
    scores = []
    for cv in CV_FILES:
        score = sum(1 for kw in cv["keywords"] if kw in text)
        scores.append((score, cv))
    scores.sort(key=lambda x: x[0], reverse=True)

    best_score = scores[0][0]
    second_score = scores[1][0] if len(scores) > 1 else 0

    # Confident if best score >= 2 and clearly ahead of second
    confidence = best_score if (best_score >= 2 and best_score > second_score) else 0
    return scores[0][1], confidence


def generate_email(job_info: dict, selected_cv_key: str = None) -> dict:
    all_cvs = get_all_cvs()
    cv_map = {cv["key"]: cv for cv in all_cvs}

    if selected_cv_key:
        cv = cv_map[selected_cv_key]
        confidence = 5
    else:
        cv, confidence = select_cv(job_info.get("requirements_summary", ""))
        cv = next(c for c in all_cvs if c["key"] == cv["key"])

    cv_text = read_cv_text(cv["path"])[:3500]

    job_title = job_info.get("job_title") or "the advertised position"
    company = job_info.get("company") or "your company"
    requirements = (job_info.get("requirements_summary") or "")[:800]

    prompt = f"""You are writing a tailored job application email. Your job is to READ the requirements carefully, then SEARCH the CV for the most relevant matching experience, skills, and tools — and highlight only those.

===== TARGET JOB =====
Position: {job_title}
Company: {company}
Requirements: {requirements}

===== MY CV =====
{cv_text}

===== YOUR TASK =====
Step 1 — Identify the 3-4 most relevant keywords/skills from the requirements.
Step 2 — Find where those exact skills or experiences appear in the CV text above.
Step 3 — Write 2 short paragraphs (~70 words total) that connect those CV facts directly to this specific job.

STRICT RULES:
- Every claim must come word-for-word or paraphrased from the CV text. No invented facts.
- Do NOT use the same opening sentence for every job — vary it based on what this role needs.
- Bold (<b>) the 2-3 skills most relevant to THIS specific job's requirements.
- No greeting line. No subject line. End with one call-to-action sentence.
- First person. Professional tone.

OUTPUT: HTML only — <p> tags for paragraphs, <b> for bolded skills. Nothing else."""

    response = get_client().models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config=_FAST_CONFIG,
    )

    import re
    raw = response.text.strip()
    raw = re.sub(r"^```(?:html)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # Convert markdown **bold** → <b> with inline style (Gmail strips <style> tags)
    raw = re.sub(
        r"\*\*(.+?)\*\*",
        r'<b style="color:#1d4ed8;font-weight:700;">\1</b>',
        raw,
    )
    plain_body = re.sub(r"<[^>]+>", "", raw)
    html_body = build_html_email(raw, job_title, company)

    return {
        "cv_path": cv["path"],
        "cv_name": cv["name"],
        "cv_filename": cv["filename"],
        "cv_key": cv["key"],
        "email_body": plain_body,
        "email_html": html_body,
        "subject": f"Application for {job_title} — Omar Shawada",
        "confidence": confidence,
    }


def build_html_email(body_html: str, job_title: str, company: str) -> str:
    # If Gemini already returned <p> tags use as-is, otherwise wrap paragraphs
    import re as _re
    if "<p>" not in body_html:
        paragraphs = "".join(
            f"<p>{p.strip()}</p>" for p in body_html.split("\n\n") if p.strip()
        )
    else:
        paragraphs = body_html
    return f"""
<div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 6px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08);">

  <!-- Header -->
  <div style="background: linear-gradient(135deg, #0f2a4a 0%, #1d4ed8 100%); padding: 30px 36px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td>
          <div style="color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: 0.3px;">Omar Shawada</div>
          <div style="color: #93c5fd; font-size: 13px; margin-top: 3px;">Production Planning &amp; Supply Chain Engineer</div>
          <div style="color: #bfdbfe; font-size: 12px; margin-top: 6px;">
            📍 Cairo, Egypt &nbsp;·&nbsp; 📞 01284475489 &nbsp;·&nbsp;
            <a href="mailto:shawada6@gmail.com" style="color: #93c5fd; text-decoration: none;">shawada6@gmail.com</a>
          </div>
        </td>
        <td align="right" valign="top">
          <a href="https://linkedin.com/in/omar-shawada"
             style="display: inline-block; background: rgba(255,255,255,0.15); color: #ffffff;
                    font-size: 12px; font-weight: 600; padding: 6px 14px; border-radius: 20px;
                    text-decoration: none; border: 1px solid rgba(255,255,255,0.3);">
            LinkedIn ↗
          </a>
        </td>
      </tr>
    </table>
  </div>

  <!-- Role badge -->
  <div style="background: #f0f6ff; padding: 10px 36px; border-bottom: 1px solid #dbeafe;">
    <span style="color: #1d4ed8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
      ✉ Job Application &nbsp;·&nbsp; {job_title}
    </span>
  </div>

  <!-- Body -->
  <div style="padding: 32px 36px;">

    <p style="margin: 0 0 20px; color: #1e293b; font-size: 15px;">Dear Hiring Manager,</p>

    <div style="color: #1e293b; font-size: 14.5px; line-height: 1.8;">
      {paragraphs}
    </div>

    <div style="margin-top: 28px;">
      <p style="margin: 0; color: #475569; font-size: 14px;">Warm regards,</p>
      <p style="margin: 6px 0 0; color: #0f2a4a; font-size: 17px; font-weight: 700;">Omar Shawada</p>
      <p style="margin: 2px 0 0; color: #64748b; font-size: 12px;">📞 01284475489 &nbsp;·&nbsp; shawada6@gmail.com</p>
    </div>
  </div>

  <!-- Footer -->
  <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px 36px; text-align: center;">
    <span style="color: #94a3b8; font-size: 11.5px;">
      📎 CV attached &nbsp;·&nbsp; Applying to: <strong style="color: #64748b;">{company}</strong>
    </span>
  </div>

</div>
""".strip()


if __name__ == "__main__":
    import json
    sample = {
        "email": "hr@example.com",
        "job_title": "Planning & MRP Head - Automotive Manufacturing",
        "company": "Lean on Hub",
        "requirements_summary": "Production planning, MRP/ERP systems, BOM accuracy, automotive manufacturing",
    }
    result = generate_email(sample)
    print(f"CV: {result['cv_name']} (confidence: {result['confidence']})")
    print(f"Subject: {result['subject']}")
    print("\n--- Email Body ---")
    print(result["email_body"])
