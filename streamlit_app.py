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

#MainMenu, footer, header { visibility: hidden; }

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


# ── Gemini EmailSession ────────────────────────────────────────────────────────
class EmailSession:
    """Manages a Gemini chat with automatic model fallback."""

    def __init__(self, api_key: str, resume_text: str):
        self.client = genai.Client(api_key=api_key)
        self.resume_text = resume_text
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

    def _send(self, message: str) -> str:
        while True:
            try:
                response = self._chat.send_message(message)
                text = response.text.strip()
                self.last_used_model = self.current_model
                self._history.append({"role": "user",  "parts": [{"text": message}]})
                self._history.append({"role": "model", "parts": [{"text": text}]})
                return text
            except Exception as exc:
                if not self._switch_model(exc):
                    raise

    def compose(self, jd: str) -> str:
        prompt = (
            f"Here is my resume:\n\n```\n{self.resume_text}\n```\n\n"
            f"Here is the job description:\n\n```\n{jd}\n```\n\n"
            "Write the cold email now."
        )
        self.jd_loaded = True
        return self._send(prompt)

    def refine(self, instruction: str) -> str:
        return self._send(instruction)

    def reset(self):
        self.model_idx = 0
        self._history = []
        self._new_chat()
        self.jd_loaded = False


# ── Session state defaults ─────────────────────────────────────────────────────
_DEFAULTS = {
    "resume_name":    None,   # filename string
    "resume_text":    None,   # extracted plain text
    "email_session":  None,   # EmailSession object
    "emails":         [],     # [(instruction_str, email_text)]
    "saved_jd":       "",     # JD locked after first generation
    "api_key":        "",
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
            raw_bytes = uploaded_file.read()
            with st.spinner("Reading PDF…"):
                try:
                    text = extract_pdf_text(raw_bytes)
                    if not text.strip():
                        st.error("No text found — is this a scanned image PDF?")
                    else:
                        st.session_state.resume_name   = uploaded_file.name
                        st.session_state.resume_text   = text
                        st.session_state.email_session = None   # reset Gemini session
                        st.session_state.emails        = []
                        st.session_state.saved_jd      = ""
                        st.toast("✅ Resume loaded!", icon="📄")
                        st.rerun()
                except Exception as exc:
                    st.error(f"PDF error: {exc}")

    # ── Resume uploader ────────────────────────────────────────────────────────
    st.markdown('<div class="sb-label">📄 Resume (PDF)</div>', unsafe_allow_html=True)

    uploaded_sidebar = st.file_uploader(
        "resume_upload_sb",
        type=["pdf"],
        label_visibility="collapsed",
        key="sidebar_uploader",
        help="Stays loaded for this browser session. Re-upload on a new tab/device.",
    )
    if uploaded_sidebar:
        load_resume(uploaded_sidebar)

    # Status badge
    if st.session_state.resume_text:
        name = st.session_state.resume_name or "resume.pdf"
        short = name[:28] + "…" if len(name) > 30 else name
        st.markdown(
            f'<div class="status-badge status-ok">✓ {short}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:0.7rem;color:#334155;">'
            f'{len(st.session_state.resume_text):,} characters extracted</div>',
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

if not st.session_state.resume_text:
    st.warning("⚠️ Please upload your resume PDF to get started.")
    uploaded_main = st.file_uploader(
        "Upload your resume PDF (drag & drop here)",
        type=["pdf"],
        key="main_uploader",
    )
    if uploaded_main:
        load_resume(uploaded_main)
    st.stop()

# Ensure Gemini session object exists
if st.session_state.email_session is None:
    try:
        st.session_state.email_session = EmailSession(
            api_key=st.session_state.api_key,
            resume_text=st.session_state.resume_text,
        )
    except Exception as exc:
        st.error(f"Could not connect to Gemini: {exc}")
        st.stop()

session: EmailSession = st.session_state.email_session

# ── Job Description input ──────────────────────────────────────────────────────
st.markdown('<div class="section-label">Job Description</div>', unsafe_allow_html=True)

jd_value = st.session_state.saved_jd if st.session_state.emails else ""

jd_input = st.text_area(
    "jd_area",
    value=jd_value,
    height=210,
    placeholder=(
        "Paste the full job description here.\n"
        "Include the recruiter's email if visible — it'll be auto-detected."
    ),
    label_visibility="collapsed",
    disabled=bool(st.session_state.emails),
)

if not st.session_state.emails:
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
            "Tip: recruiter email in the JD is auto-extracted for you</p>",
            unsafe_allow_html=True,
        )

    if generate_clicked:
        if not jd_input.strip():
            st.warning("Please paste a job description first.")
        else:
            with st.spinner("Crafting your email with Gemini…"):
                try:
                    email_text = session.compose(jd_input)
                    st.session_state.emails.append(("Initial draft", email_text))
                    st.session_state.saved_jd = jd_input
                except Exception as exc:
                    st.error(f"Gemini error: {exc}")
                    st.stop()
            st.rerun()

else:
    st.markdown(
        "<p style='color:#334155;font-size:0.75rem;margin-top:0.25rem;'>"
        "🔒 JD locked for this session. "
        "Click <b>New Email (Reset)</b> in the sidebar to start over.</p>",
        unsafe_allow_html=True,
    )


# ── Display generated email ────────────────────────────────────────────────────
def render_email_html(raw: str) -> str:
    """Wrap special lines in styled spans."""
    out = []
    for line in raw.split("\n"):
        if line.startswith("TO:"):
            out.append(f'<span class="email-to">{line}</span>')
        elif line.startswith("Subject:"):
            out.append(f'<span class="email-subject">{line}</span>')
        elif any(line.startswith(p) for p in SIGNOFF_PREFIXES):
            out.append(f'<span class="email-signoff">{line}</span>')
        else:
            out.append(line)
    return "\n".join(out)


if st.session_state.emails:
    _, latest_email = st.session_state.emails[-1]

    st.markdown('<div class="section-label">Generated Email</div>', unsafe_allow_html=True)

    st.markdown(
        f"<span style='color:#334155;font-size:0.72rem;'>Model</span>"
        f"<span class='model-tag'>{session.last_used_model}</span>",
        unsafe_allow_html=True,
    )

    # Email card
    email_html = render_email_html(latest_email)
    st.markdown(f'<div class="email-card">{email_html}</div>', unsafe_allow_html=True)

    # Recipient highlight
    recipient = extract_email_from_text(latest_email)
    if recipient:
        st.markdown(
            f"<div class='recipient-row'>"
            f"📬 <b style='color:#34d399;'>Recipient:</b>&nbsp;"
            f"<code style='background:#0c1830;padding:0.18rem 0.5rem;"
            f"border-radius:4px;color:#34d399;font-size:0.82rem;'>{recipient}</code>"
            f"&nbsp;<span style='color:#334155;font-size:0.75rem;'>"
            f"— paste into Gmail's To: field</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Copy section
    with st.expander("📋  Copy email text"):
        st.text_area(
            "copy_box",
            value=latest_email,
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
