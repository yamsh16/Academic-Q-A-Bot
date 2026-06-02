import streamlit as st
import os
import json
import re
from groq import Groq
import tempfile

# ── Document parsers ──────────────────────────────────────────────────────────
def extract_text_from_pdf(file_bytes: bytes) -> str:
    import pypdf, io
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def extract_text_from_docx(file_bytes: bytes) -> str:
    import docx, io
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs)

def extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")

def extract_text(uploaded_file) -> str:
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    raw = uploaded_file.read()
    if ext == "pdf":
        return extract_text_from_pdf(raw)
    elif ext in ("docx", "doc"):
        return extract_text_from_docx(raw)
    elif ext == "txt":
        return extract_text_from_txt(raw)
    raise ValueError(f"Unsupported file type: .{ext}")

# ── Q&A generator ─────────────────────────────────────────────────────────────
def generate_qa(client: Groq, text: str, num_q: int, difficulty: str) -> list[dict]:
    prompt = f"""You are an expert academic tutor. Based on the document content below, generate exactly {num_q} high-quality question-and-answer pairs.

Difficulty level: {difficulty}
- Easy: factual recall questions
- Medium: comprehension and application questions  
- Hard: analysis, synthesis, and evaluation questions

Return ONLY a JSON array with this exact structure (no markdown, no explanation):
[
  {{"question": "...", "answer": "...", "type": "..."}},
  ...
]

The "type" field should be one of: Factual, Conceptual, Analytical, Application

Document content:
{text[:6000]}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=3000,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)

# ── Streamlit UI ──────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Academic Q&A Generator",
        page_icon="📚",
        layout="wide",
    )

    # ── Custom CSS ────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Source+Sans+3:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Source Sans 3', sans-serif; }

    .main { background: #0f0f1a; }
    .stApp { background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%); }
    
    .hero-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #e8c97a, #f5e6b8, #c9a84c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        line-height: 1.2;
    }
    .hero-sub {
        color: #8b8fa8;
        font-size: 1.05rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    .upload-zone {
        border: 2px dashed #3a3a5c;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        background: rgba(255,255,255,0.02);
        margin-bottom: 1.5rem;
        transition: border-color 0.3s;
    }
    .upload-zone:hover { border-color: #c9a84c; }

    .qa-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(200,168,76,0.2);
        border-radius: 14px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1.2rem;
        transition: transform 0.2s, border-color 0.3s;
    }
    .qa-card:hover {
        transform: translateY(-2px);
        border-color: rgba(200,168,76,0.5);
    }

    .q-label {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #c9a84c;
        margin-bottom: 0.4rem;
    }
    .q-text {
        font-family: 'Playfair Display', serif;
        font-size: 1.05rem;
        color: #e8e8f0;
        margin-bottom: 1rem;
        line-height: 1.55;
    }
    .a-label {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #6b9e8a;
        margin-bottom: 0.4rem;
    }
    .a-text {
        color: #b0c8bf;
        font-size: 0.95rem;
        line-height: 1.65;
    }
    .type-badge {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 20px;
        margin-bottom: 0.8rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .type-Factual     { background: rgba(100,150,220,0.15); color: #7ab0e8; border: 1px solid rgba(100,150,220,0.3); }
    .type-Conceptual  { background: rgba(180,100,220,0.15); color: #c880e8; border: 1px solid rgba(180,100,220,0.3); }
    .type-Analytical  { background: rgba(220,140,60,0.15);  color: #e8a840; border: 1px solid rgba(220,140,60,0.3); }
    .type-Application { background: rgba(80,180,120,0.15);  color: #60c890; border: 1px solid rgba(80,180,120,0.3); }

    .stat-box {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .stat-num { font-size: 1.8rem; font-weight: 700; color: #c9a84c; }
    .stat-lbl { font-size: 0.78rem; color: #666; text-transform: uppercase; letter-spacing: 0.1em; }

    div[data-testid="stSidebar"] {
        background: rgba(15,15,30,0.95) !important;
        border-right: 1px solid rgba(255,255,255,0.07);
    }
    .sidebar-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.1rem;
        color: #c9a84c;
        margin-bottom: 1rem;
    }

    .stButton button {
        background: linear-gradient(135deg, #c9a84c, #e8c97a) !important;
        color: #0f0f1a !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.65rem 2rem !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.05em;
        transition: opacity 0.2s !important;
    }
    .stButton button:hover { opacity: 0.85 !important; }

    .stSelectbox label, .stSlider label, .stTextInput label {
        color: #8b8fa8 !important;
        font-size: 0.85rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown('<div class="sidebar-title">⚙ Configuration</div>', unsafe_allow_html=True)

        api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="Free key at console.groq.com",
        )

        st.divider()

        num_questions = st.slider("Number of Questions", 3, 20, 8)
        difficulty = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"])

        st.divider()
        st.markdown("""
        <div style="color:#555; font-size:0.78rem; line-height:1.6">
        <b style="color:#c9a84c">Supported formats</b><br>
        📄 PDF &nbsp;·&nbsp; 📝 DOCX &nbsp;·&nbsp; 📃 TXT<br><br>
        <b style="color:#c9a84c">Get a free API key</b><br>
        <a href="https://console.groq.com" target="_blank" style="color:#7ab0e8">console.groq.com</a>
        </div>
        """, unsafe_allow_html=True)

    # ── Main area ─────────────────────────────────────────────────────────────
    st.markdown('<div class="hero-title">Academic Q&A Generator</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Upload an academic document and instantly generate study questions & answers</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Drop your document here",
        type=["pdf", "docx", "doc", "txt"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="stat-box"><div class="stat-num">1</div><div class="stat-lbl">File Uploaded</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{num_questions}</div><div class="stat-lbl">Questions</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{difficulty}</div><div class="stat-lbl">Difficulty</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🎓 Generate Q&A Pairs", use_container_width=False):
            if not api_key:
                st.error("Please enter your Groq API key in the sidebar.")
                return

            with st.spinner("Reading document..."):
                try:
                    text = extract_text(uploaded_file)
                except Exception as e:
                    st.error(f"Could not read file: {e}")
                    return

            if len(text.strip()) < 100:
                st.warning("The document appears too short or empty.")
                return

            with st.spinner(f"Generating {num_questions} {difficulty.lower()} questions..."):
                try:
                    client = Groq(api_key=api_key)
                    qa_pairs = generate_qa(client, text, num_questions, difficulty)
                except json.JSONDecodeError:
                    st.error("Could not parse the AI response. Please try again.")
                    return
                except Exception as e:
                    st.error(f"API error: {e}")
                    return

            st.session_state["qa_pairs"] = qa_pairs
            st.session_state["doc_name"] = uploaded_file.name

    # ── Render results ─────────────────────────────────────────────────────────
    if "qa_pairs" in st.session_state:
        qa_pairs = st.session_state["qa_pairs"]
        doc_name = st.session_state.get("doc_name", "document")

        st.markdown(f"### 📖 Q&A for *{doc_name}*")
        st.markdown(f"<div style='color:#555;font-size:0.85rem;margin-bottom:1.5rem'>{len(qa_pairs)} questions generated</div>", unsafe_allow_html=True)

        for i, qa in enumerate(qa_pairs, 1):
            q_type = qa.get("type", "Factual")
            st.markdown(f"""
            <div class="qa-card">
                <div class="type-badge type-{q_type}">{q_type}</div>
                <div class="q-label">Q{i}</div>
                <div class="q-text">{qa.get("question", "")}</div>
                <div class="a-label">Answer</div>
                <div class="a-text">{qa.get("answer", "")}</div>
            </div>
            """, unsafe_allow_html=True)

        # Download as text
        export = "\n\n".join(
            f"Q{i}: {qa['question']}\nA: {qa['answer']}"
            for i, qa in enumerate(qa_pairs, 1)
        )
        st.download_button(
            "⬇ Download Q&A as .txt",
            data=export,
            file_name=f"qa_{doc_name.rsplit('.',1)[0]}.txt",
            mime="text/plain",
        )

if __name__ == "__main__":
    main()
