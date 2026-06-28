# Job Application Email Composer

A Streamlit AI web app that reads your resume and a job description, then uses **Google Gemini** to write a short, humanized, personalized cold email.  No AI slop, no "I hope this message finds you well."

**Live app:** https://email-jd-personalized.streamlit.app/

---

## Features

- Upload resume as **PDF or image** (PNG/JPG/JPEG) — or just paste plain text
- Paste job description text **or upload a screenshot** — Gemini reads it directly
- Auto-detects **recipient email** and **WhatsApp/phone number** from the JD
- **One-click copy** for email body, subject line, and recipient address
- **Gmail-friendly HTML copy** — pastes with formatting intact into Gmail/Outlook
- **Conversational refinement** — just tell it what to change, it remembers context
- **Version history** — every refinement is tracked
- **Automatic model fallback** — tries the best Gemini model first, silently switches if rate-limited

---

## Model Chain

The app always tries the best available model first and falls back automatically on errors or rate limits:

```
gemini-3.5-flash  →  gemini-3-flash  →  gemini-2.5-flash  →  gemini-2.5-flash-lite  →  gemini-3.1-flash-lite
```

No crashes, no quota drama.

---

## Setup (local)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Gemini API key

Get a free key at: https://aistudio.google.com/app/apikey

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY = "your_api_key_here"
```

**Mac / Linux:**
```bash
export GEMINI_API_KEY=your_api_key_here
```

Or create a `.env` file in the project root:
```
GEMINI_API_KEY=your_api_key_here
```

### 3. Run

```bash
streamlit run streamlit_app.py
```

---

## How to use

1. **Enter your Gemini API key** when prompted (only needed if not set via env/secrets)
2. **Upload your resume** — PDF, image, or paste text directly
3. **Paste the job description** or upload a screenshot of it
4. Click **Generate Email**
5. **Refine conversationally** — type things like:
   - `shorten it more`
   - `make it more casual`
   - `mention my FastAPI experience`
   - `change the subject line`
6. Click **Next Application** to start fresh for a new job

---

## Customization

The system prompt in `streamlit_app.py` (`build_system_prompt()`) is hardcoded for one user's background, tone, and contact details. To use this for yourself, update:

- `CONTACT_BLOCK` — your name, phone, email, LinkedIn, GitHub
- `build_system_prompt()` — your preferred tone, experience years logic, notice period, etc.

---

## CLI version

A terminal-based version is also available:

```bash
python email_composer.py
```

Drop a `.pdf` resume in the project folder, run the script, paste a JD, type `END`. Same model chain, same fallback logic, no browser needed.

---

## Stack

- **Python** + **Streamlit** (web UI)
- **Google Gemini** via `google-genai` SDK (LLM)
- **pdfplumber** (PDF text extraction)
- **Regex** (email/WhatsApp detection)
