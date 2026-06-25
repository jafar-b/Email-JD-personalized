# Job Application Email Composer

A terminal-based tool that reads your **resume PDF** and a **job description**, then uses **Google Gemini** to write a short, humanized, personalized cold email you can send directly.

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Gemini API key

**Windows (Command Prompt):**
```cmd
set GEMINI_API_KEY=your_api_key_here
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY = "your_api_key_here"
```

**Mac / Linux:**
```bash
export GEMINI_API_KEY=your_api_key_here
```

Get your free API key at: https://aistudio.google.com/app/apikey

### 3. Place your resume PDF

Drop your resume PDF (any `.pdf` file) into this folder. The script will auto-detect it.

### 4. Run

```bash
python email_composer.py
```

---

## How to use

1. **Paste a job description** when prompted, then type `END` on a new line.
2. The tool will **generate a draft email** and display the recipient email (if found in JD).
3. **Refine naturally** — just type things like:
   - `shorten it more`
   - `make it less formal`
   - `punch up the subject line`
   - `mention my FastAPI experience`
4. The conversation **remembers context** — every refinement builds on the previous draft.
5. Type `new` to start with a new job description, or `quit` to exit.

---

## Model

Uses `gemini-2.5-flash` by default — fast, cost-effective, and highly capable.
