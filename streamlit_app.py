"""
Job Application Email Composer — Streamlit Web App
===================================================
Upload your resume PDF once per browser session.
Paste a job description → get a polished cold email → refine conversationally.
"""

import io
import os
import re
from datetime import date
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

# ── Page config (must be the very first Streamlit call) ────────────────────────
st.set_page_config(
    page_title="Job Email Composer · Gemini",
    page_icon="✉️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Dependency checks ──────────────────────────────────────────────────────────
try:
    import pdfplumber
except ImportError:
    st.error("Missing dependency `pdfplumber` — run: pip install -r requirements.txt")
    st.stop()

try:
    from google import genai
    from google.genai import types
except ImportError:
    st.error("Missing dependency `google-genai` — run: pip install -r requirements.txt")
    st.stop()

# Load .env for local dev (silently ignored if not present / not installed)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Apply font safely to main wrapper without overriding icons */
.stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp label, .stApp button {
    font-family: 'Inter', sans-serif !important;
}

#MainMenu, footer { visibility: hidden; }
header { background: transparent !important; }

.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 4rem !important;
    max-width: 800px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #06091a 0%, #0c1830 60%, #08122a 100%);
    border-right: 1px solid #1a2e50;
}
[data-testid="stSidebarContent"] { padding: 1.2rem 1rem 2rem; }

.app-brand {
    text-align: center;
    padding: 0.6rem 0 1.4rem;
    border-bottom: 1px solid #1a2e50;
    margin-bottom: 1.4rem;
}
.app-brand .icon { font-size: 2.4rem; }
.app-brand h2 {
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    background: linear-gradient(120deg, #38bdf8 0%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0.25rem 0 0 !important;
    line-height: 1.2 !important;
}
.app-brand .powered {
    font-size: 0.65rem;
    color: #334155;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 0.2rem;
}

.sb-label {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #475569;
    margin: 1rem 0 0.4rem;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.7rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
    margin: 0.4rem 0 0.6rem;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.status-ok  { background:rgba(16,185,129,.15); border:1px solid rgba(16,185,129,.3); color:#34d399; }
.status-err { background:rgba(239,68,68,.12);  border:1px solid rgba(239,68,68,.25);  color:#f87171; }

.exp-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.28rem 0.6rem;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    background: rgba(56,189,248,.12);
    border: 1px solid rgba(56,189,248,.25);
    color: #38bdf8;
}

/* ── Page title ── */
.page-title {
    font-size: 1.9rem;
    font-weight: 700;
    background: linear-gradient(120deg, #38bdf8 0%, #818cf8 55%, #c084fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.15;
}
.page-sub {
    font-size: 0.85rem;
    color: #475569;
    margin: 0.3rem 0 2rem;
}

.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #475569;
    margin: 1.6rem 0 0.5rem;
}

/* ── Email card ── */
.email-card {
    background: linear-gradient(145deg, #0b192e 0%, #0f172a 100%);
    border: 1px solid rgba(30,64,175,.45);
    border-radius: 14px;
    padding: 1.8rem 2.2rem;
    margin: 0.6rem 0 0.2rem;
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.78;
    font-size: 0.91rem;
    color: #cbd5e1;
    box-shadow: 0 6px 28px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.04);
}
.email-to      { color: #34d399; font-weight: 600; }
.email-subject { color: #38bdf8; font-weight: 600; font-size: 0.96rem; }
.email-signoff { color: #4a6380; }

.model-tag {
    display: inline-block;
    font-size: 0.63rem;
    font-weight: 500;
    letter-spacing: 0.06em;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    background: rgba(129,140,248,.15);
    border: 1px solid rgba(129,140,248,.3);
    color: #818cf8;
    margin-left: 0.5rem;
    vertical-align: middle;
}

.recipient-row {
    margin: 0.5rem 0 1rem;
    font-size: 0.82rem;
}

/* ── Buttons ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(120deg, #1d4ed8, #7c3aed) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.45rem 1.4rem !important;
    letter-spacing: 0.02em !important;
    transition: all .2s !important;
    box-shadow: 0 2px 12px rgba(124,58,237,.25) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 5px 20px rgba(124,58,237,.4) !important;
}

/* ── Inputs ── */
textarea, [data-baseweb="textarea"] textarea {
    background: #0c1830 !important;
    border: 1px solid #1a3a60 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 0.89rem !important;
    line-height: 1.65 !important;
}
textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,.2) !important;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    border: 1px dashed #1a3a60;
    border-radius: 16px;
    margin-top: 2rem;
    color: #334155;
}
.empty-state .icon { font-size: 3.2rem; margin-bottom: 1rem; }
.empty-state .title { font-size: 1rem; font-weight: 500; color: #475569; }
.empty-state .hint  { font-size: 0.78rem; margin-top: 0.4rem; }

div.stSpinner > div { border-top-color: #38bdf8 !important; }
</style>
""", unsafe_allow_html=True)


# ── Constants ──────────────────────────────────────────────────────────────────
CONTACT_BLOCK = """Regards,
Jafar Beldar
+91 7262067842
beldarjafar@gmail.com
LinkedIn: linkedin.com/in/jafarbeldar
GitHub: https://github.com/jafar-b"""

# Quality-ordered model chain — always tries best first, falls back on error
MODEL_CHAIN = [
    "gemini-3.5-flash",
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
]

SIGNOFF_PREFIXES = ("Regards,", "Jafar", "+91", "beldarj", "LinkedIn:", "GitHub:")


# ── Core helpers ───────────────────────────────────────────────────────────────
def calc_experience() -> str:
    start = date(2025, 1, 1)
    elapsed_days = (date.today() - start).days
    years = round(elapsed_days / 365.25, 1)
    formatted = str(int(years)) if years == int(years) else f"{years:.1f}"
    return f"{formatted}+"


def build_system_prompt() -> str:
    exp = calc_experience()
    return f"""You are an expert career coach and professional email writer with deep knowledge of Indian professional communication style.

Your job is to write COLD JOB APPLICATION EMAILS. Follow these rules strictly:

⚠️ CRITICAL OVERRIDE — EXPERIENCE YEARS: The ONLY correct value for years of experience is **{exp}**.
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


def extract_pdf_text(file_bytes: bytes) -> str:
    parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t.strip())
    return "\n\n".join(parts)


def extract_email_from_text(text: str) -> Optional[str]:
    matches = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return matches[0] if matches else None


def extract_whatsapp_number(text: str) -> Optional[str]:
    """Detects WhatsApp or general contact phone numbers inside a job description."""
    # Pattern 1: WhatsApp links (wa.me/xxx)
    wa_link = re.search(r"(?:wa\.me|whatsapp\.com/send\?phone=)(\d+)", text, re.IGNORECASE)
    if wa_link:
        return "+" + wa_link.group(1)
        
    # Pattern 2: Explicitly labeled WhatsApp contact
    wa_match = re.search(r"(?:whatsapp|wa\.me|wa)\s*(?:us\s*at|at|number|:|-)?\s*(\+?\d{1,4}[-.\s]?\d{2,5}[-.\s]?\d{3,5}[-.\s]?\d{3,5})", text, re.IGNORECASE)
    if wa_match:
        num = wa_match.group(1).strip()
        digits_only = re.sub(r"\D", "", num)
        if 8 <= len(digits_only) <= 15:
            if len(digits_only) == 10 and not num.startswith("+"):
                return f"+91 {num}"
            return num
            
    # Pattern 3: General phone contact keywords
    phone_match = re.search(r"(?:contact|mobile|call|tel|phone)\s*(?::|-)?\s*(\+?\d{1,4}[-.\s]?\d{2,5}[-.\s]?\d{3,5}[-.\s]?\d{3,5})", text, re.IGNORECASE)
    if phone_match:
        num = phone_match.group(1).strip()
        digits_only = re.sub(r"\D", "", num)
        if 8 <= len(digits_only) <= 15:
            if len(digits_only) == 10 and not num.startswith("+"):
                return f"+91 {num}"
            return num
            
    # Pattern 4: Any international format number (+91..., +971..., etc.)
    any_intl = re.search(r"(\+\d{1,4}[-.\s]?\d{2,5}[-.\s]?\d{3,5}[-.\s]?\d{3,5})", text)
    if any_intl:
        num = any_intl.group(1).strip()
        digits_only = re.sub(r"\D", "", num)
        if 8 <= len(digits_only) <= 15:
            return num

    return None


def make_gmail_friendly_html(raw: str) -> str:
    """Creates a rich-text HTML representation of the email for Gmail/Outlook."""
    # Convert newlines to breaks
    html = raw.replace("\n", "<br>")
    
    # Apply linkification
    # 1. Email address
    html = re.sub(
        r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        r'<a href="mailto:\1" style="color: #15c; text-decoration: underline;">\1</a>',
        html
    )
    # 2. GitHub URL (with https://)
    html = re.sub(
        r"(https?://[^\s<>#\"'{}|\\^\[\]`]+)",
        r'<a href="\1" target="_blank" style="color: #15c; text-decoration: underline;">\1</a>',
        html
    )
    # 3. LinkedIn link without protocol
    html = re.sub(
        r"(?<!href=\")(?<!href=\"https://)(linkedin\.com/in/[^\s<>#\"'{}|\\^\[\]`]+)",
        r'<a href="https://\1" target="_blank" style="color: #15c; text-decoration: underline;">\1</a>',
        html
    )
    # 4. Phone number
    def repl_phone(match):
        num = match.group(1)
        clean_num = num.replace(" ", "")
        return f'<a href="tel:{clean_num}" style="color: #15c; text-decoration: underline;">{num}</a>'
    
    html = re.sub(r"(\+91\s*\d{10})", repl_phone, html)
    
    # Wrap in a standard sans-serif font container
    return f'<div style="font-family: Arial, sans-serif; font-size: 14.5px; line-height: 1.65; color: #222222;">{html}</div>'


def st_copy_button(text_to_copy: str, label: str, key: str, html_to_copy: str = None):
    """Generates a styled, functional inline copy-to-clipboard button using JS."""
    # Clean up formatting for JS string literal safety
    escaped_text = (
        text_to_copy
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    
    if html_to_copy:
        escaped_html = (
            html_to_copy
            .replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )
        js_write = f"""
        const text = "{escaped_text}";
        const html = "{escaped_html}";
        if (navigator.clipboard && navigator.clipboard.write) {{
            const textBlob = new Blob([text], {{ type: 'text/plain' }});
            const htmlBlob = new Blob([html], {{ type: 'text/html' }});
            const item = new ClipboardItem({{
                'text/plain': textBlob,
                'text/html': htmlBlob
            }});
            navigator.clipboard.write([item])
                .then(() => showSuccess())
                .catch(() => fallbackCopy(text));
        }} else {{
            fallbackCopy(text);
        }}
        """
    else:
        js_write = f"""
        const text = "{escaped_text}";
        if (navigator.clipboard && navigator.clipboard.writeText) {{
            navigator.clipboard.writeText(text)
                .then(() => showSuccess())
                .catch(() => fallbackCopy(text));
        }} else {{
            fallbackCopy(text);
        }}
        """

    html_code = f"""
    <div style="margin: 0; padding: 0; display: inline-block; vertical-align: middle;">
        <button id="btn-{key}" style="
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 6px;
            color: #e2e8f0;
            padding: 5px 10px;
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 500;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        ">
            <span style="font-size: 11px;">📋</span> {label}
        </button>
    </div>
    <script>
    const btn = document.getElementById('btn-{key}');
    btn.addEventListener('click', function() {{
        {js_write}
    }});
    
    function fallbackCopy(text) {{
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        try {{
            document.execCommand('copy');
            showSuccess();
        }} catch (err) {{
            console.error('Failed to copy', err);
        }}
        document.body.removeChild(ta);
    }}
    
    function showSuccess() {{
        btn.innerHTML = '<span>✅</span> Copied!';
        btn.style.background = 'linear-gradient(135deg, #065f46, #064e3b)';
        btn.style.borderColor = 'rgba(52, 211, 153, 0.4)';
        btn.style.color = '#34d399';
        setTimeout(() => {{
            btn.innerHTML = '<span style="font-size: 11px;">📋</span> {label}';
            btn.style.background = 'linear-gradient(135deg, #1e293b, #0f172a)';
            btn.style.borderColor = 'rgba(56, 189, 248, 0.25)';
            btn.style.color = '#e2e8f0';
        }}, 1800);
    }}
    </script>
    """
    components.html(html_code, height=30)


def make_whatsapp_link(num: str) -> str:
    """Formats a phone number into a direct click-to-chat WhatsApp link."""
    digits = re.sub(r"\D", "", num)
    # Default to India (+91) if it's a raw 10-digit number
    if len(digits) == 10:
        return f"https://wa.me/91{digits}"
    elif len(digits) == 11 and digits.startswith("0"):
        return f"https://wa.me/91{digits[1:]}"
    else:
        return f"https://wa.me/{digits}"


def st_link_button(url: str, label: str):
    """Generates a styled inline link button matching st_copy_button appearance."""
    html_code = f"""
    <div style="margin: 0; padding: 0; display: inline-block; vertical-align: middle;">
        <a href="{url}" target="_blank" style="
            background: linear-gradient(135deg, #10b981, #059669);
            border: 1px solid rgba(52, 211, 153, 0.3);
            border-radius: 6px;
            color: white;
            padding: 5px 10px;
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 500;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        ">
            <span style="font-size: 11px;">💬</span> {label}
        </a>
    </div>
    """
    components.html(html_code, height=30)


# ── Gemini EmailSession ────────────────────────────────────────────────────────
class EmailSession:
    """Manages a Gemini chat with automatic model fallback."""

    def __init__(self, api_key: str, resume_text: str = None, resume_image_bytes: bytes = None, resume_image_mime: str = None):
        self.client = genai.Client(api_key=api_key)
        self.resume_text = resume_text
        self.resume_image_bytes = resume_image_bytes
        self.resume_image_mime = resume_image_mime
        self.model_idx = 0
        self._history: list = []
        self.last_used_model = MODEL_CHAIN[0]
        self.jd_loaded = False
        self._chat = None
        self._new_chat()

    @property
    def current_model(self) -> str:
        return MODEL_CHAIN[self.model_idx]

    def _new_chat(self):
        self._chat = self.client.chats.create(
            model=self.current_model,
            config=types.GenerateContentConfig(
                system_instruction=build_system_prompt(),
            ),
            history=self._history,
        )

    def _switch_model(self, exc: Exception) -> bool:
        if self.model_idx >= len(MODEL_CHAIN) - 1:
            return False
        self.model_idx += 1
        self._new_chat()
        return True

    def _send(self, message, history_placeholder: str = None) -> str:
        while True:
            try:
                response = self._chat.send_message(message)
                text = response.text.strip()
                self.last_used_model = self.current_model
                
                # If history_placeholder is provided (like when sending images), save that instead of the raw list/part in history
                user_text = history_placeholder if history_placeholder else message
                
                self._history.append({"role": "user",  "parts": [{"text": user_text}]})
                self._history.append({"role": "model", "parts": [{"text": text}]})
                return text
            except Exception as exc:
                if not self._switch_model(exc):
                    raise

    def compose(self, jd_text: str = None, jd_image_bytes: bytes = None, jd_image_mime: str = None) -> str:
        prompt_parts = []
        history_desc = "Initial draft request. "
        
        # 1. Resume (either text or image)
        if self.resume_text:
            prompt_parts.append(f"Here is my resume:\n\n```\n{self.resume_text}\n```\n\n")
            history_desc += "Resume: [Text] "
        elif self.resume_image_bytes:
            prompt_parts.append("Here is my resume image/screenshot:")
            resume_part = types.Part.from_bytes(
                data=self.resume_image_bytes,
                mime_type=self.resume_image_mime
            )
            prompt_parts.append(resume_part)
            prompt_parts.append("\n\n")
            history_desc += "Resume: [Image] "
            
        # 2. Job Description (either text or image)
        if jd_text:
            prompt_parts.append(f"Here is the job description text:\n\n```\n{jd_text}\n```\n\n")
            history_desc += f"Job Description Text:\n{jd_text}"
            
        if jd_image_bytes:
            prompt_parts.append("Here is the job description screenshot/image:")
            image_part = types.Part.from_bytes(
                data=jd_image_bytes,
                mime_type=jd_image_mime
            )
            prompt_parts.append(image_part)
            prompt_parts.append("\n\n")
            history_desc += "[Job Description Image Uploaded]"
            
        prompt_parts.append("Analyze the job description and write the cold email now.")
        
        self.jd_loaded = True
        return self._send(prompt_parts, history_placeholder=history_desc)

    def refine(self, instruction: str) -> str:
        return self._send(instruction)

    def reset(self):
        self.model_idx = 0
        self._history = []
        self._new_chat()
        self.jd_loaded = False


# ── Session state defaults ─────────────────────────────────────────────────────
_DEFAULTS = {
    "resume_name":        None,   # filename string
    "resume_text":        None,   # extracted plain text
    "resume_image_bytes": None,   # image bytes if image resume
    "resume_image_mime":  None,   # image mime if image resume
    "email_session":      None,   # EmailSession object
    "emails":             [],     # [(instruction_str, email_text)]
    "saved_jd":           "",     # JD locked after first generation
    "api_key":            "",
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="app-brand">
        <div class="icon">✉️</div>
        <h2>Job Email Composer</h2>
        <div class="powered">Powered by Google Gemini</div>
    </div>
    """, unsafe_allow_html=True)

    # ── API Key (env → Streamlit secrets → manual input) ──────────────────────
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    if not api_key:
        st.markdown('<div class="sb-label">Gemini API Key</div>', unsafe_allow_html=True)
        typed_key = st.text_input(
            "api_key_field",
            type="password",
            placeholder="AIza...",
            label_visibility="collapsed",
        )
        if typed_key:
            api_key = typed_key
    st.session_state.api_key = api_key

    # Helper to process file content and update session state
    def load_resume(uploaded_file):
        if uploaded_file is not None and uploaded_file.name != st.session_state.resume_name:
            file_name = uploaded_file.name
            file_ext = file_name.split(".")[-1].lower()
            
            # Reset existing resume values
            st.session_state.resume_name   = file_name
            st.session_state.resume_text   = None
            st.session_state.resume_image_bytes = None
            st.session_state.resume_image_mime = None
            st.session_state.email_session = None   # reset Gemini session
            st.session_state.emails        = []
            st.session_state.saved_jd      = ""
            
            if file_ext == "pdf":
                raw_bytes = uploaded_file.read()
                with st.spinner("Reading PDF…"):
                    try:
                        text = extract_pdf_text(raw_bytes)
                        if not text.strip():
                            st.error("No text found — is this a scanned image PDF?")
                        else:
                            st.session_state.resume_text = text
                            st.toast("✅ Resume PDF loaded!", icon="📄")
                            st.rerun()
                    except Exception as exc:
                        st.error(f"PDF error: {exc}")
            elif file_ext in ["png", "jpg", "jpeg"]:
                st.session_state.resume_image_bytes = uploaded_file.read()
                st.session_state.resume_image_mime = uploaded_file.type
                st.toast("✅ Resume image loaded!", icon="📸")
                st.rerun()
            else:
                st.error("Unsupported file format. Please upload a PDF or an Image.")

    # ── Resume uploader ────────────────────────────────────────────────────────
    st.markdown('<div class="sb-label">📄 Resume (PDF / Image / Text)</div>', unsafe_allow_html=True)

    uploaded_sidebar = st.file_uploader(
        "resume_upload_sb",
        type=["pdf", "png", "jpg", "jpeg"],
        label_visibility="collapsed",
        key="sidebar_uploader",
        help="Stays loaded for this browser session. Re-upload on a new tab/device.",
    )
    if uploaded_sidebar:
        load_resume(uploaded_sidebar)

    with st.expander("✍️ Or paste plain text"):
        sidebar_pasted = st.text_area(
            "Paste resume text:",
            height=180,
            label_visibility="collapsed",
            placeholder="Jafar Beldar\nSkills: Python, Gemini, Vector DBs...",
            key="sidebar_pasted_area"
        )
        if st.button("💾 Save Text", use_container_width=True, key="sidebar_save_btn"):
            if sidebar_pasted.strip():
                st.session_state.resume_name   = "Pasted Text Resume"
                st.session_state.resume_text   = sidebar_pasted.strip()
                st.session_state.resume_image_bytes = None
                st.session_state.resume_image_mime = None
                st.session_state.email_session = None
                st.session_state.emails        = []
                st.session_state.saved_jd      = ""
                st.toast("✅ Resume text saved!", icon="📝")
                st.rerun()
            else:
                st.warning("Please paste text first.")

    # Status badge
    if st.session_state.resume_text or st.session_state.resume_image_bytes:
        name = st.session_state.resume_name or "resume"
        short = name[:28] + "…" if len(name) > 30 else name
        st.markdown(
            f'<div class="status-badge status-ok">✓ {short}</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.resume_text:
            st.markdown(
                f'<div style="font-size:0.7rem;color:#334155;">'
                f'{len(st.session_state.resume_text):,} characters extracted</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="font-size:0.7rem;color:#334155;">'
                f'Image Resume loaded</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="status-badge status-err">✗ No resume loaded</div>',
            unsafe_allow_html=True,
        )

    exp = calc_experience()
    st.markdown(
        f'<div style="margin-top:0.8rem"><div class="exp-chip">⏱ {exp} years experience</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Reset button (only visible when an email exists)
    if st.session_state.emails:
        if st.button("🔄  New Email (Reset)", use_container_width=True):
            if st.session_state.email_session:
                st.session_state.email_session.reset()
            st.session_state.emails   = []
            st.session_state.saved_jd = ""
            st.rerun()

    st.markdown("""
    <div style="margin-top:auto; padding-top:2rem;
                font-size:0.63rem; color:#1e3a5f; text-align:center; line-height:1.6;">
        Jafar Beldar · Job Email Composer<br>
        Resume loaded per session · Emails not stored
    </div>
    """, unsafe_allow_html=True)


# ── Main ───────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">Job Email Composer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-sub">Paste a job description → get a polished cold email → refine until perfect</div>',
    unsafe_allow_html=True,
)

# Gates
if not st.session_state.api_key:
    st.info("👈  Enter your **Gemini API Key** in the sidebar to get started.")
    st.stop()

if not st.session_state.resume_text and not st.session_state.resume_image_bytes:
    st.warning("⚠️ Please upload or paste your resume to get started.")
    
    tab_upload, tab_paste = st.tabs(["📁 Drag & Drop PDF / Image", "📝 Paste Text Resume"])
    
    with tab_upload:
        uploaded_main = st.file_uploader(
            "Upload your resume PDF or Image (drag & drop here)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="main_uploader",
            label_visibility="collapsed"
        )
        if uploaded_main:
            load_resume(uploaded_main)
            
    with tab_paste:
        main_pasted = st.text_area(
            "Paste your plain text resume below:",
            height=250,
            placeholder="Jafar Beldar\nAI Engineer\nSkills: Python, Gemini, Vector DBs...",
            label_visibility="collapsed",
            key="main_pasted_area"
        )
        if st.button("💾 Save Resume Text", type="primary"):
            if main_pasted.strip():
                st.session_state.resume_name   = "Pasted Text Resume"
                st.session_state.resume_text   = main_pasted.strip()
                st.session_state.resume_image_bytes = None
                st.session_state.resume_image_mime = None
                st.session_state.email_session = None
                st.session_state.emails        = []
                st.session_state.saved_jd      = ""
                st.toast("✅ Resume text loaded!", icon="📝")
                st.rerun()
            else:
                st.error("Please paste your resume text first.")
    st.stop()

# Ensure Gemini session object exists
if st.session_state.email_session is None:
    try:
        st.session_state.email_session = EmailSession(
            api_key=st.session_state.api_key,
            resume_text=st.session_state.resume_text,
            resume_image_bytes=st.session_state.resume_image_bytes,
            resume_image_mime=st.session_state.resume_image_mime
        )
    except Exception as exc:
        st.error(f"Could not connect to Gemini: {exc}")
        st.stop()

session: EmailSession = st.session_state.email_session

# ── Job Description input ──────────────────────────────────────────────────────
st.markdown('<div class="section-label">Job Description</div>', unsafe_allow_html=True)

if not st.session_state.emails:
    tab_jd_text, tab_jd_img = st.tabs(["📝 Paste JD Text", "📸 Upload JD Image"])
    
    jd_input = ""
    jd_image_bytes = None
    jd_image_mime = None
    
    with tab_jd_text:
        jd_text = st.text_area(
            "jd_text_area",
            height=210,
            placeholder=(
                "Paste the full job description here.\n"
                "Include the recruiter's email if visible — it'll be auto-detected."
            ),
            label_visibility="collapsed",
            key="jd_text_field"
        )
        if jd_text.strip():
            jd_input = jd_text.strip()
            
    with tab_jd_img:
        uploaded_jd_img = st.file_uploader(
            "Upload Job Description screenshot/image",
            type=["png", "jpg", "jpeg"],
            key="jd_image_field",
            help="Upload a screenshot of the job description flyer, LinkedIn post, or WhatsApp image."
        )
        if uploaded_jd_img:
            jd_image_bytes = uploaded_jd_img.read()
            jd_image_mime = uploaded_jd_img.type
            st.image(uploaded_jd_img, caption="Uploaded Job Description Screenshot", use_container_width=True)

    col_btn, col_tip = st.columns([1, 3])
    with col_btn:
        generate_clicked = st.button(
            "✨  Generate Email",
            type="primary",
            use_container_width=True,
        )
    with col_tip:
        st.markdown(
            "<p style='color:#334155;font-size:0.78rem;padding-top:0.55rem;'>"
            "Tip: Gemini will read your screenshot directly to extract skills and contact details!</p>",
            unsafe_allow_html=True,
        )

    if generate_clicked:
        if not jd_input and not jd_image_bytes:
            st.warning("Please paste a job description text or upload a screenshot first.")
        else:
            with st.spinner("Crafting your email with Gemini…"):
                try:
                    email_text = session.compose(
                        jd_text=jd_input,
                        jd_image_bytes=jd_image_bytes,
                        jd_image_mime=jd_image_mime
                    )
                    st.session_state.emails.append(("Initial draft", email_text))
                    if jd_input:
                        st.session_state.saved_jd = jd_input
                    elif uploaded_jd_img:
                        st.session_state.saved_jd = f"[JD Screenshot: {uploaded_jd_img.name}]"
                except Exception as exc:
                    st.error(f"Gemini error: {exc}")
                    st.stop()
            st.rerun()

else:
    # JD is locked because email has been generated
    saved_val = st.session_state.saved_jd
    if saved_val.startswith("[JD Screenshot:"):
        st.info(f"🔒 {saved_val} is locked for this session.")
    else:
        st.text_area(
            "jd_locked_view",
            value=saved_val,
            height=150,
            disabled=True,
            label_visibility="collapsed"
        )
    st.markdown(
        "<p style='color:#334155;font-size:0.75rem;margin-top:0.25rem;'>"
        "🔒 JD locked for this session. "
        "Click <b>New Email (Reset)</b> in the sidebar to start over.</p>",
        unsafe_allow_html=True,
    )


# ── Display generated email ────────────────────────────────────────────────────
def parse_generated_email(raw: str):
    """Splits the raw generated email text into recipient, subject, and body components."""
    lines = raw.split("\n")
    to_email = None
    subject = None
    body_lines = []
    
    in_body = False
    for line in lines:
        stripped = line.strip()
        if not in_body:
            if stripped.startswith("TO:"):
                to_email = stripped[3:].strip()
                continue
            elif stripped.startswith("Subject:"):
                subject = stripped[8:].strip()
                continue
            elif stripped == "":
                continue
            else:
                in_body = True
        
        if in_body:
            body_lines.append(line)
            
    return to_email, subject, "\n".join(body_lines).strip()


def make_clickable_html(line: str) -> str:
    """Detects contact info in sign-off and returns them as HTML anchors."""
    # 1. Email address
    line = re.sub(
        r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        r'<a href="mailto:\1" style="color: #38bdf8; text-decoration: underline;">\1</a>',
        line
    )
    # 2. GitHub URL (with https://)
    line = re.sub(
        r"(https?://[^\s<>#\"'{}|\\^\[\]`]+)",
        r'<a href="\1" target="_blank" style="color: #38bdf8; text-decoration: underline;">\1</a>',
        line
    )
    # 3. LinkedIn link without protocol
    if "LinkedIn:" in line and "href=" not in line:
        line = re.sub(
            r"(linkedin\.com/in/[^\s<>#\"'{}|\\^\[\]`]+)",
            r'<a href="https://\1" target="_blank" style="color: #38bdf8; text-decoration: underline;">\1</a>',
            line
        )
    # 4. Phone number
    if "+91" in line and "href=" not in line:
        match = re.search(r"(\+91\s*\d{10})", line)
        if match:
            num = match.group(1)
            clean_num = num.replace(" ", "")
            line = line.replace(num, f'<a href="tel:{clean_num}" style="color: #38bdf8; text-decoration: underline;">{num}</a>')
    return line


def render_email_html(raw: str) -> str:
    """Wrap special lines in styled spans and make contact links clickable."""
    out = []
    for line in raw.split("\n"):
        if line.startswith("TO:"):
            out.append(f'<span class="email-to">{line}</span>')
        elif line.startswith("Subject:"):
            out.append(f'<span class="email-subject">{line}</span>')
        elif any(line.startswith(p) for p in SIGNOFF_PREFIXES):
            clickable_line = make_clickable_html(line)
            out.append(f'<span class="email-signoff">{clickable_line}</span>')
        else:
            out.append(line)
    return "\n".join(out)


if st.session_state.emails:
    _, latest_email = st.session_state.emails[-1]
    
    # Parse email parts
    recipient, subject, email_body = parse_generated_email(latest_email)

    st.markdown('<div class="section-label">Generated Email</div>', unsafe_allow_html=True)

    # Extract recipient and WhatsApp from JD
    recipient_jd = extract_email_from_text(st.session_state.saved_jd) if st.session_state.saved_jd else None
    # Fallback to recipient parsed from the email headers (crucial if only an image was uploaded)
    if not recipient_jd and recipient:
        recipient_jd = recipient

    whatsapp_jd = extract_whatsapp_number(st.session_state.saved_jd) if st.session_state.saved_jd else None

    # 1. Recipient Row
    col_recip, col_recip_copy = st.columns([2, 1])
    with col_recip:
        if recipient_jd:
            st.markdown(
                f"<div class='recipient-row' style='margin-top:0.4rem;'>"
                f"📬 <b style='color:#34d399;'>Recipient:</b>&nbsp;"
                f"<code style='background:#0c1830;padding:0.18rem 0.5rem;"
                f"border-radius:4px;color:#34d399;font-size:0.82rem;'>{recipient_jd}</code>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='recipient-row' style='margin-top:0.4rem; color: #475569; font-style: italic; font-size: 0.82rem;'>"
                f"📬 Recipient: No email address found in JD"
                f"</div>",
                unsafe_allow_html=True,
            )
    with col_recip_copy:
        if recipient_jd:
            st_copy_button(recipient_jd, "Copy Recipient", "recipient_email")

    # 2. WhatsApp/Phone Row
    col_wa, col_wa_copy = st.columns([2, 1])
    with col_wa:
        if whatsapp_jd:
            st.markdown(
                f"<div class='recipient-row' style='margin-top:0.4rem;'>"
                f"💬 <b style='color:#10b981;'>WhatsApp/Phone:</b>&nbsp;"
                f"<code style='background:#0c1830;padding:0.18rem 0.5rem;"
                f"border-radius:4px;color:#10b981;font-size:0.82rem;'>{whatsapp_jd}</code>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='recipient-row' style='margin-top:0.4rem; color: #475569; font-style: italic; font-size: 0.82rem;'>"
                f"💬 WhatsApp/Phone: No number found in JD"
                f"</div>",
                unsafe_allow_html=True,
            )
    with col_wa_copy:
        if whatsapp_jd:
            wa_link = make_whatsapp_link(whatsapp_jd)
            st_link_button(wa_link, "Open WhatsApp")

    # 3. Subject Row
    if subject:
        col_subj, col_subj_copy = st.columns([2, 1])
        with col_subj:
            st.markdown(
                f"<div class='recipient-row' style='margin-top:0.4rem;'>"
                f"📌 <b style='color:#38bdf8;'>Subject:</b>&nbsp;"
                f"<code style='background:#0c1830;padding:0.18rem 0.5rem;"
                f"border-radius:4px;color:#38bdf8;font-size:0.82rem;'>{subject}</code>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_subj_copy:
            st_copy_button(subject, "Copy Subject", "email_subject")

    # 3. Model info & Copy Email Body Header
    col_meta, col_copy = st.columns([2, 1])
    with col_meta:
        st.markdown(
            f"<div style='margin-top: 0.15rem;'>"
            f"<span style='color:#334155;font-size:0.72rem; vertical-align: middle;'>Model</span>"
            f"<span class='model-tag'>{session.last_used_model}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_copy:
        gmail_html = make_gmail_friendly_html(email_body)
        st_copy_button(email_body, "Copy Email Body", "email_text", html_to_copy=gmail_html)

    # Email card (renders only the body of the email)
    email_html = render_email_html(email_body)
    st.markdown(f'<div class="email-card">{email_html}</div>', unsafe_allow_html=True)

    # Copy section
    with st.expander("📋  Copy email text"):
        st.text_area(
            "copy_box",
            value=email_body,
            height=220,
            label_visibility="collapsed",
            key="copy_area",
        )
        st.caption("Select all text above (Ctrl+A / Cmd+A) then copy.")

    # Version history
    if len(st.session_state.emails) > 1:
        with st.expander(f"📜  Version history  ({len(st.session_state.emails)} versions)"):
            for i, (instr, _) in enumerate(st.session_state.emails):
                is_latest = (i == len(st.session_state.emails) - 1)
                color  = "#38bdf8" if is_latest else "#334155"
                prefix = "→ " if is_latest else "   "
                label  = "Initial draft" if instr == "Initial draft" else (
                    f'"{instr[:55]}…"' if len(instr) > 57 else f'"{instr}"'
                )
                st.markdown(
                    f"<div style='font-size:0.78rem;color:{color};"
                    f"padding:0.25rem 0.5rem;border-left:2px solid #1e3a60;"
                    f"margin:0.2rem 0;font-style:italic;'>"
                    f"{prefix}v{i+1}: {label}</div>",
                    unsafe_allow_html=True,
                )

    # ── Refinement ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Refine the Email</div>', unsafe_allow_html=True)

    refine_input = st.text_area(
        "refine_area",
        height=80,
        placeholder=(
            'e.g. "shorten it more" · "make it more casual" · '
            '"add a mention of LangChain" · "change the subject line"'
        ),
        label_visibility="collapsed",
        key="refine_input",
    )

    col_r1, col_r2 = st.columns([1, 4])
    with col_r1:
        refine_clicked = st.button(
            "✏️  Apply",
            type="primary",
            use_container_width=True,
        )

    if refine_clicked:
        if not refine_input.strip():
            st.warning("Describe what you'd like to change.")
        else:
            with st.spinner("Refining…"):
                try:
                    refined = session.refine(refine_input)
                    st.session_state.emails.append((refine_input, refined))
                except Exception as exc:
                    st.error(f"Gemini error: {exc}")
            st.rerun()
