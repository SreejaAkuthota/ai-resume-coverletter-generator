import os
import streamlit as st
 from datetime import date
 from prompts import build_resume_prompt, build_cover_letter_prompt
 from utils import LLMClient, StyleConfig, safe_filename
 from export import render_resume_md, render_cover_md, md_to_docx, save_docx
 from jinja2 import Template
 import os, json
 
+# ─────────────────────────────────────────────────────────────────────────────
+# Read keys from Streamlit **Secrets** (Cloud) and expose them as env vars.
+# This lets the rest of the code (utils.LLMClient) keep using os.getenv(...).
+# In your app dashboard, set:
+#   Settings → Secrets:
+#     OPENAI_API_KEY = "sk-..."
+#     OPENAI_MODEL   = "gpt-4o-mini"   (optional)
+# ─────────────────────────────────────────────────────────────────────────────
+try:
+    if "OPENAI_API_KEY" in st.secrets and not os.getenv("OPENAI_API_KEY"):
+        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
+    if "OPENAI_MODEL" in st.secrets and not os.getenv("OPENAI_MODEL"):
+        os.environ["OPENAI_MODEL"] = st.secrets["OPENAI_MODEL"]
+except Exception:
+    # st.secrets may not exist locally; ignore and rely on .env
+    pass
+

st.set_page_config(page_title="AI Resume & Cover Letter Generator", page_icon="📝", layout="wide")

st.markdown("""
<style>
/* subtle glassy cards */
.block-container { padding-top: 2rem; }
.css-18ni7ap, .stTextInput, .stTextArea { backdrop-filter: blur(6px); }
.stButton>button { border-radius: 12px; padding: 0.5rem 1rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.title("📝 AI Resume & Cover Letter Generator")
st.caption("Prompt-engineered LLM app to tailor resumes and cover letters to a target job.")

with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.setdefault("style_tone", "professional, confident")
    tone = st.text_input("Tone", st.session_state["style_tone"])
    seniority = st.selectbox("Seniority", ["entry", "junior", "mid", "mid-senior", "senior", "lead"], index=3)
    layout = st.selectbox("Layout", ["modern ATS-friendly", "classic", "two-column (ATS-safe)"], index=0)
    style = StyleConfig(tone=tone, seniority=seniority, layout=layout)

    st.divider()
    st.link_button("Advanced Settings", "pages/1_Advanced_Settings.py")

st.subheader("Candidate Profile")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Full Name", value="Amulya Goli")
    title = st.text_input("Target Title", value="Revenue Cycle Analyst | Medical Coding Specialist")
    location = st.text_input("Location", value="Aurora, IL")
    email = st.text_input("Email", value="amulyagoli@example.com")
with col2:
    phone = st.text_input("Phone", value="+1 (555) 123-4567")
    linkedin = st.text_input("LinkedIn URL", value="https://linkedin.com/in/yourprofile")
    portfolio = st.text_input("Portfolio URL", value="https://your-portfolio.com")

skills = st.text_area("Core Skills (comma-separated)", value="ICD-10-CM, CPT/HCPCS, Denial Management, KPI Reporting, Epic, SQL, Python, Streamlit")
experience = st.text_area("Experience Summary (paste bullets or paragraphs)", height=160, value="- Managed high-volume outstanding claims; reduced AR >90 by 22%\n- Performed KPI/denial trend reporting with SQL dashboards\n- Collaborated with providers to resolve coding/documentation gaps")
education = st.text_area("Education & Certifications", value="MBA in Healthcare Informatics; CPC (A)")

existing_resume = st.text_area("Existing Resume Text (optional)", help="Paste your current resume to enrich the output", height=120)

st.subheader("Target Job")
job_title = st.text_input("Job Title", value="Claims Coding Specialist (Medical Coder)")
job_company = st.text_input("Company", value="UChicago Medicine")
job_summary = st.text_area("JD Summary", value="Support clinic services with revenue cycle functions including training, charge capture, and correct coding edits.")
job_requirements = st.text_area("Top Requirements", value="ICD-10-CM, CPT/HCPCS, NCCI edits, Epic, payer rules, KPI reporting")

cand = {
    "name": name, "title": title, "location": location, "email": email,
    "phone": phone, "linkedin": linkedin, "portfolio": portfolio,
    "skills": skills, "experience": experience, "education": education
}
job = {"title": job_title, "company": job_company, "summary": job_summary, "requirements": job_requirements}

tab_resume, tab_cover = st.tabs(["📄 Resume", "✉️ Cover Letter"])

if "gen_resume" not in st.session_state:
    st.session_state["gen_resume"] = None
if "gen_cover" not in st.session_state:
    st.session_state["gen_cover"] = None

with tab_resume:
    st.markdown("### Generate Tailored Resume")
    if st.button("🚀 Generate Resume"):
        try:
            client = LLMClient()
            prompt = build_resume_prompt(cand, job, style.model_dump(), existing_resume or None)
            data = client.complete_json(prompt)
            # Prepare MD using template
            with open("templates/resume_template.md.j2", "r", encoding="utf-8") as f:
                tmpl = f.read()
            md = render_resume_md(data | {"cand": cand}, tmpl)
            st.session_state["gen_resume"] = md
            st.success("Resume generated!")
        except Exception as e:
            st.error(f"Generation error: {e}")

    if st.session_state["gen_resume"]:
        st.markdown("#### Preview (Markdown)")
        st.markdown(st.session_state["gen_resume"])
        if st.download_button("⬇️ Download as .md", data=st.session_state["gen_resume"], file_name=f"{safe_filename(name)}_resume.md", mime="text/markdown"):
            pass
        # DOCX export
        doc = md_to_docx(st.session_state["gen_resume"], title=f"{name} – Resume")
        docx_path = f"{safe_filename(name)}_resume.docx"
        doc.save(docx_path)
        with open(docx_path, "rb") as fh:
            st.download_button("⬇️ Download as .docx", data=fh, file_name=docx_path, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

with tab_cover:
    st.markdown("### Generate Tailored Cover Letter")
    if st.button("✍️ Generate Cover Letter"):
        try:
            client = LLMClient()
            # Use highlights from resume if available
            resume_highlights = None
            if st.session_state.get("gen_resume"):
                resume_highlights = st.session_state["gen_resume"][:2000]
            prompt = build_cover_letter_prompt(cand, job, style.model_dump(), resume_highlights=resume_highlights)
            md = client.complete_markdown(prompt, temperature=float(st.session_state.get("temperature", 0.6)))
            st.session_state["gen_cover"] = md
            st.success("Cover letter generated!")
        except Exception as e:
            st.error(f"Generation error: {e}")

    if st.session_state["gen_cover"]:
        st.markdown("#### Preview (Markdown)")
        st.markdown(st.session_state["gen_cover"])
        if st.download_button("⬇️ Download as .md", data=st.session_state["gen_cover"], file_name=f"{safe_filename(name)}_cover_letter.md", mime="text/markdown"):
            pass
        doc = md_to_docx(st.session_state["gen_cover"], title=f"{name} – Cover Letter")
        docx_path = f"{safe_filename(name)}_cover_letter.docx"
        doc.save(docx_path)
        with open(docx_path, "rb") as fh:
            st.download_button("⬇️ Download as .docx", data=fh, file_name=docx_path, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

st.markdown("---")
st.caption("Built with Streamlit • Prompt engineering patterns • OpenAI API")
