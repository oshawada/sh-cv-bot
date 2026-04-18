# Workflow: LinkedIn Job Application via Telegram Bot

## Objective
Automate job applications from LinkedIn posts. User sends a screenshot → bot reads it with Gemini Vision → selects the right CV → writes a cover letter → previews for approval → sends via Gmail.

## Required Inputs
- Screenshot of a LinkedIn post (or any job ad) containing an email address
- `.env` file with: `TELEGRAM_BOT_TOKEN`, `GOOGLE_AI_API_KEY`, `GMAIL_SENDER`
- Gmail OAuth token (generated on first run via browser)

## Steps

1. **User sends photo** to the Telegram bot
2. **[extract_job_info.py]** — Bot downloads photo and sends to Gemini 2.0 Flash Vision
   - Extracts: `email`, `job_title`, `company`, `requirements_summary`
   - If no email found → bot replies with warning, stops
3. **[generate_email.py]** — Selects CV based on keyword matching:
   - Operations → `Omar_Shawada_Operations_CV_ATS.pdf`
   - Planning/Scheduling → `Omar_Shawada_Planning_CV_ATS.pdf`
   - Production/Manufacturing → `Omar_Shawada_ProductionPlanning_CV_ATS.pdf`
   - Gemini writes professional English email body (~150 words)
4. **Bot sends preview** in Telegram with: To, Subject, CV name, email body
5. **User reviews** → types `/confirm` to send or `/cancel` to discard
6. **[send_gmail.py]** — Sends email via Gmail API with PDF attachment
7. **Bot confirms** with ✅ and message ID

## Tools Used
- `tools/extract_job_info.py` — Gemini Vision extraction
- `tools/generate_email.py` — CV selection + cover letter generation
- `tools/send_gmail.py` — Gmail API sending
- `tools/telegram_bot.py` — Main bot orchestrator

## Expected Output
Email delivered to the employer's inbox with:
- Professional cover letter body
- PDF CV attachment (most relevant CV auto-selected)

## Edge Cases & Known Issues

### No email in screenshot
- Bot replies: "لم أجد إيميل في الصورة"
- User should crop/zoom the image so the email is clearly visible

### Ambiguous job type (CV selection)
- Bot uses keyword scoring — highest score wins
- If all scores are 0 (no matching keywords), defaults to Operations CV
- To override: send another photo after cancelling and mention the role type more clearly in caption (future feature)

### Gmail OAuth (first run)
- First time running `telegram_bot.py`, a browser window will open for Google login
- Log in as shawada6@gmail.com and grant Gmail send permissions
- Token is saved to `credentials/gmail_token.pickle` — won't ask again

### Gmail token expired
- Token auto-refreshes if refresh_token is valid
- If refresh fails: delete `credentials/gmail_token.pickle` and restart bot

### Gemini rate limits
- Free tier: 15 requests/minute for gemini-2.0-flash
- Each job application uses 2 Gemini calls (vision + text generation)
- If rate limited: wait ~1 minute and resend the photo

### Running the bot
```bash
cd "c:\Users\Omar Shawada\Desktop\telegram email"
python tools/telegram_bot.py
```
