# Google CLI Project

## What This Project Is
This project uses the GWS CLI (Google Workspace CLI) to interact with Google Drive, Docs, Gmail, Calendar, and Sheets directly from the terminal.

## Always Do This at Session Start
```bash
export PATH="$PATH:/c/Users/Omar Shawada/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin"
```

## Key Info
- Google account: shawada6@gmail.com
- GCP Project: helpful-range-462320-r0
- gws version: 0.22.5
- Auth credentials saved at: C:\Users\Omar Shawada\.config\gws\credentials.enc
- No need to re-login unless token expires

## Use the GWS CLI Skill
For any Google Workspace task (YouTube → Doc → Gmail, Drive, Sheets, etc.), use the `gws-cli` skill — it has all commands and workflows ready.

## Common Tasks
- Summarize YouTube video → Google Doc → send via Gmail
- List Drive files: `gws drive files list --params '{"pageSize": 10}'`
- Create Doc: `gws docs documents create --json '{"title": "Title"}'`
- Send email: `gws gmail +send --to email --subject "..." --body "..."`
