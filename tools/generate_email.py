# tools/generate_email.py
# Purpose: Select the right CV and generate a cover letter based on CV content + job requirements
# Inputs: job_info dict, selected_cv (optional override)
# Outputs: dict {cv_path, cv_name, cv_filename, email_body, subject, confidence}

import os
from google import genai
from dotenv import load_dotenv
from pypdf import PdfReader
from download_cvs import CV_FILES, get_all_cvs

load_dotenv()

_client = None


def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))
    return _client


def read_cv_text(cv_path: str) -> str:
    reader = PdfReader(cv_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


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

    cv_text = read_cv_text(cv["path"])

    job_title = job_info.get("job_title") or "the advertised position"
    company = job_info.get("company") or "your company"
    requirements = job_info.get("requirements_summary") or ""

    prompt = f"""You are a world-class executive career coach and persuasive copywriter who specializes in writing job application emails that make HR managers immediately pick up the phone to schedule an interview.

Your goal: write an email body so compelling that the reader finishes it thinking "I need to meet this person TODAY."

JOB DETAILS:
- Position: {job_title}
- Company: {company}
- Key requirements: {requirements}

OMAR'S ACTUAL CV CONTENT (use SPECIFIC details, numbers, and achievements — never be vague):
{cv_text}

WRITING RULES (follow every single one):
1. OPEN with a bold, confident hook that immediately signals value — NOT "I am writing to express my interest." Start with what Omar DELIVERS.
2. Connect Omar's SPECIFIC achievements directly to the company's pain points. Name exact tools, systems, results from the CV.
3. Create a "this person is rare" feeling — highlight 2 unique things Omar has done that most candidates cannot claim.
4. Keep it tight: 3 short paragraphs, ~160 words total. Every sentence must earn its place. No filler.
5. End with a confident, natural call to action.
6. Tone: confident, direct, warm. High-performer who knows their value.
7. Write in FIRST PERSON (I, my, me). Never use "he/Omar/third person".
8. Write in English. NO greeting line, NO subject line.

FORMATTING:
- Wrap important keywords, tools, achievements, and numbers in <b> tags.
- Examples of what to bold: tool names, system names, metrics, key skills matching the job.
- Return the email as HTML paragraphs using <p> tags with <b> for bold words.
- NO other HTML tags. Just <p> and <b>."""

    response = get_client().models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
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
