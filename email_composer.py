"""
Job Application Email Composer
================================
Uses Google Gemini to generate humanized, personalized cold emails
based on your resume (PDF) and a job description.

Setup:
  1. Place your resume as 'resume.pdf' in this directory.
  2. Copy .env.example to .env and fill in your values.
  3. Install dependencies: pip install -r requirements.txt
  4. Run: python email_composer.py
"""

import os
import sys
import re
import glob
import textwrap
import math
from datetime import date
from pathlib import Path

# -- Third-party ---------------------------------------------------------------
try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("Missing dependency: run  pip install -r requirements.txt")

try:
    import pdfplumber
except ImportError:
    sys.exit("Missing dependency: run  pip install -r requirements.txt")

try:
    from google import genai
    from google.genai import types
except ImportError:
    sys.exit("Missing dependency: run  pip install -r requirements.txt")

# Load .env file from the project root (silently ignored if not present)
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# -- ANSI color helpers ---------------------------------------------------------
RESET   = "\033[0m"
BOLD    = "\033[1m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
DIM     = "\033[2m"
MAGENTA = "\033[95m"

def c(text, color):  return f"{color}{text}{RESET}"
def header(text):    print(f"\n{BOLD}{CYAN}{'-'*60}{RESET}\n{BOLD}{CYAN}  {text}{RESET}\n{BOLD}{CYAN}{'-'*60}{RESET}\n")
def success(text):   print(f"{GREEN}  {text}{RESET}")
def warn(text):      print(f"{YELLOW}  {text}{RESET}")
def error(text):     print(f"{RED}  {text}{RESET}")
def info(text):      print(f"{DIM}  {text}{RESET}")
def label(text):     print(f"\n{BOLD}{MAGENTA}{text}{RESET}")

HELP_TEXT = f"""
{BOLD}Available commands:{RESET}
  new       Start fresh with a new job description
  help      Show this help message
  quit      Exit the program

{BOLD}Refinement examples (just type naturally):{RESET}
  shorten it more
  make it sound more casual
  add a mention of my Python skills
  change the subject line to be catchier
  make the opening punchier
"""

CONTACT_BLOCK = """Regards,
Jafar Beldar
+91 7262067842
beldarjafar@gmail.com
LinkedIn: linkedin.com/in/jafarbeldar
GitHub: https://github.com/jafar-b"""


def calc_experience() -> str:
    """Compute years of experience from Jan 1 2025 to today, e.g. '1.5+'.
    Uses actual elapsed days for decimal precision (1.4, 1.5, 1.6 …).
    """
    start = date(2025, 1, 1)   # professional start date
    today = date.today()
    elapsed_days = (today - start).days
    years = round(elapsed_days / 365.25, 1)   # 1-decimal precision
    formatted = str(int(years)) if years == int(years) else f"{years:.1f}"
    return f"{formatted}+"


def build_system_prompt() -> str:
    exp = calc_experience()
    return f"""You are an expert career coach and professional email writer with deep knowledge of Indian professional communication style.

Your job is to write COLD JOB APPLICATION EMAILS. Follow these rules strictly:

 CRITICAL OVERRIDE — EXPERIENCE YEARS: The ONLY correct value for years of experience is **{exp}**.
   DO NOT derive experience from dates on the resume. DO NOT calculate it yourself.
   Always use exactly "{exp} years" — never any other number.

1. TONE: Confident, warm, and slightly Indian in flavour — direct and respectful without being stiff or over-formal.
   Think: how a sharp Indian professional emails a recruiter. No-nonsense, genuine, gets to the point fast.
2. LENGTH: Short and punchy. 5-7 sentences total across 2 paragraphs. Cut anything that doesn't add value.
3. STRUCTURE - follow this exactly:
   a. If a recipient email was found in the JD, output it FIRST on its own line:
         TO: <email_address>
      Then one blank line.
   b. Subject line on its own line:
         Subject: <specific, punchy subject>
      Then one blank line.
   c. Greeting line (e.g. "Hi Vishnu," or "Hello [Hiring Team],")
      Then one blank line.
   d. PARAGRAPH 1 - Hook (2-3 sentences):
      - State the specific role and company by name.
      - Mention {exp} years of experience — always write this as a numeral ({exp}), NEVER spell it out as a word.
      - Lead with the single most relevant achievement from the resume that matches the JD.
   e. One blank line.
   f. PARAGRAPH 2 - Match + logistics (2-3 sentences):
      - Mention 1-2 specific tools/skills from the resume that directly match the JD.
      - Notice period: write it as "My notice period is 30 days" — do NOT say "I am currently on a notice period".
      - Available for an immediate interview.
      - End with a short, confident call to action.
   g. One blank line.
   h. SIGN-OFF - always end with EXACTLY this text, word for word:
{CONTACT_BLOCK}

4. EXPERIENCE FORMAT: Always write experience as a numeral + "years" e.g. "{exp} years". Never spell the number as a word.
5. NOTICE PERIOD: Say "My notice period is 30 days" — NOT "I am currently on a notice period".
6. PERSONALIZATION: Reference the specific role, company name, and matching skills from the resume.
7. NO FLUFF: Never use: "I hope this email finds you well", "I am writing to express my interest",
   "Please find attached", "I wanted to reach out", or any generic opener.
8. RELOCATION: If the job location in the JD is outside India (e.g. UAE, Dubai, USA, UK, Singapore, etc.),
   also mention in Paragraph 2: "I am open to immediate relocation to [specific location]."
   If the job is in India or location is unclear, do NOT mention relocation.
9. Output ONLY the email text. No disclaimers, no notes, no markdown formatting.

When the user asks to shorten, refine, change tone, or tweak - apply the feedback and return the new version only.
Always preserve the sign-off block exactly as specified above.
"""


def find_resume() -> Path:
    pdfs = glob.glob(str(Path(__file__).parent / "*.pdf"))
    if not pdfs:
        error("No PDF found in this directory. Place your resume.pdf here and retry.")
        sys.exit(1)
    if len(pdfs) > 1:
        warn(f"Multiple PDFs found. Using: {Path(pdfs[0]).name}")
    return Path(pdfs[0])


def extract_pdf_text(path: Path) -> str:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
    full_text = "\n\n".join(text_parts)
    if not full_text.strip():
        error(f"Could not extract any text from '{path.name}'. Is it a scanned image PDF?")
        sys.exit(1)
    return full_text


def extract_email_from_text(text: str):
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None


# Quality-ordered model chain — always tries best first, falls back on error
MODEL_CHAIN = [
    "gemini-3.5-flash",       # best quality
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",  # highest RPD — most reliable last-resort
]


def init_gemini():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        error("GEMINI_API_KEY is not set in your .env file or environment.")
        info("Add it to your .env:  GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    info(f"Model chain: {' -> '.join(MODEL_CHAIN)}")
    return client, list(MODEL_CHAIN)


class EmailSession:
    def __init__(self, client, model_list: list, resume_text: str):
        self.client          = client
        self.model_list      = model_list
        self.model_idx       = 0           # index into model_list
        self.resume_text     = resume_text
        self.jd_loaded       = False
        self.last_used_model = model_list[0]
        self._history        = []          # manually tracked [{role, parts}] for model switching
        self._new_chat()

    @property
    def current_model(self) -> str:
        return self.model_list[self.model_idx]

    def _new_chat(self):
        """Create a fresh chat on the current model, replaying any existing history."""
        self.chat = self.client.chats.create(
            model=self.current_model,
            config=types.GenerateContentConfig(
                system_instruction=build_system_prompt(),
            ),
            history=self._history,
        )

    def _switch_model(self, exc: Exception) -> bool:
        """Try to switch to the next fallback model. Returns True if switched."""
        if self.model_idx >= len(self.model_list) - 1:
            return False   # no more fallbacks

        failed = self.current_model
        self.model_idx += 1
        nxt = self.current_model

        exc_str = str(exc)
        if "503" in exc_str or "UNAVAILABLE" in exc_str or "high demand" in exc_str.lower():
            reason = "is currently experiencing high demand"
        elif "429" in exc_str or "quota" in exc_str.lower() or "rate" in exc_str.lower():
            reason = "has hit its rate/quota limit"
        else:
            reason = f"returned an error"

        warn(f"'{failed}' {reason}. Switching to {nxt} ...")

        # Replay our manually tracked history on the new model
        self._new_chat()
        return True

    def _send(self, message: str) -> str:
        """Send a message with automatic model fallback on any error."""
        while True:
            try:
                response = self.chat.send_message(message)
                text = response.text.strip()
                self.last_used_model = self.current_model   # track which model responded
                self._history.append({"role": "user",  "parts": [{"text": message}]})
                self._history.append({"role": "model", "parts": [{"text": text}]})
                return text
            except Exception as exc:
                if not self._switch_model(exc):
                    raise   # all models exhausted — surface to caller

    def compose(self, jd: str) -> str:
        prompt = (
            f"Here is my resume:\n\n"
            f"```\n{self.resume_text}\n```\n\n"
            f"Here is the job description:\n\n"
            f"```\n{jd}\n```\n\n"
            "Write the cold email now."
        )
        self.jd_loaded = True
        return self._send(prompt)

    def refine(self, instruction: str) -> str:
        if not self.jd_loaded:
            return "No email drafted yet. Please paste a job description first."
        return self._send(instruction)

    def reset(self):
        self.model_idx = 0      # back to best model
        self._history  = []     # clear conversation history
        self._new_chat()
        self.jd_loaded = False


def collect_multiline_input(prompt_text: str) -> str:
    print(f"{YELLOW}{prompt_text}{RESET}")
    print(f"{DIM}(Paste your text, then type  END  on a new line and press Enter){RESET}\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def collect_refinement_input() -> str:
    """Multi-line aware refinement prompt.
    - Commands (new/quit/help) on the first line execute immediately.
    - Single instructions: type and press Enter on a blank line.
    - Multi-line pastes: press Enter on a blank line when done (or type END).
    """
    print(f"{YELLOW}Refine the email, or type  new  /  quit  /  help:{RESET}")
    print(f"{DIM}(Single instruction: type it and press Enter twice. "
          f"Multi-line paste: end with a blank line or END){RESET}")
    lines = []
    first_prompt = True
    while True:
        try:
            prefix = f"{CYAN}> {RESET}" if first_prompt else "  "
            line = input(prefix)
            first_prompt = False
        except (KeyboardInterrupt, EOFError):
            return "quit"

        stripped = line.strip()

        # Single-word commands on the very first line
        if not lines and stripped.lower() in ("quit", "exit", "q", "new", "reset", "n", "help", "h", "?"):
            return stripped

        # Explicit END terminator
        if stripped.upper() == "END":
            break

        # Blank line = submit (only after at least one content line)
        if stripped == "" and lines:
            break

        lines.append(line)

    return "\n".join(lines).strip()


def display_email(raw: str):
    lines = raw.split("\n")
    print()
    print(f"{BOLD}{'='*64}{RESET}")
    for line in lines:
        if line.startswith("TO:"):
            print(f"  {BOLD}{GREEN}{line}{RESET}")
        elif line.startswith("Subject:"):
            print(f"  {BOLD}{CYAN}{line}{RESET}")
        else:
            print(f"  {line}")
    print(f"{BOLD}{'='*64}{RESET}")

    to_match = re.match(r"TO:\s*(.+)", lines[0].strip()) if lines else None
    if to_match:
        label("  Recipient email (copy-paste this into Gmail To: field):")
        print(f"  {BOLD}{GREEN}{to_match.group(1).strip()}{RESET}\n")


def main():
    print(f"""
{BOLD}{CYAN}
  +==================================================+
  |   Job Email Composer  *  Powered by Gemini       |
  +==================================================+
{RESET}""")

    resume_path = find_resume()
    info(f"Loading resume: {resume_path.name} ...")
    resume_text = extract_pdf_text(resume_path)
    success(f"Resume loaded ({len(resume_text):,} characters)")

    info("Connecting to Gemini ...")
    client, model_list = init_gemini()
    session = EmailSession(client, model_list, resume_text)
    success("Ready!\n")

    print(HELP_TEXT)

    while True:
        jd = collect_multiline_input("Paste the Job Description below:")

        if not jd:
            warn("No input received. Try again.")
            continue

        recipient = extract_email_from_text(jd)
        if not recipient:
            warn("No email address detected in the JD. The model will still compose the email.")

        header("Generating your email ...")
        try:
            email_text = session.compose(jd)
        except Exception as exc:
            error(f"All models exhausted. Last error: {exc}")
            info("Please try again in a moment.")
            continue

        display_email(email_text)
        info(f"Generated by: {session.last_used_model}")

        while True:
            user_input = collect_refinement_input()

            if not user_input:
                continue

            cmd = user_input.lower().strip()

            if cmd in ("quit", "exit", "q"):
                print(f"\n{BOLD}{CYAN}Goodbye! Good luck with your applications.{RESET}\n")
                sys.exit(0)

            if cmd in ("new", "reset", "n"):
                session.reset()
                break

            if cmd in ("help", "h", "?"):
                print(HELP_TEXT)
                continue

            header("Refining ...")
            try:
                email_text = session.refine(user_input)
            except Exception as exc:
                error(f"All models exhausted. Last error: {exc}")
                info("Please try again in a moment.")
                continue

            display_email(email_text)
            info(f"Generated by: {session.last_used_model}")


if __name__ == "__main__":
    main()
