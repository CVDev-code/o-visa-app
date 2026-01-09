import streamlit as st
from dotenv import load_dotenv

from src.pdf_text import extract_text_from_pdf_bytes
from src.openai_terms import suggest_ovisa_terms
from src.pdf_highlighter import highlight_terms_in_pdf_bytes

load_dotenv()

st.set_page_config(page_title="O-1 PDF Highlighter", layout="wide")

st.title("O-1 PDF Highlighter")
st.caption("Upload press PDFs → auto-detect O-1 evidence → download annotated files")

uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Upload at least one PDF to begin.")
    st.stop()

st.divider()

if "terms_by_file" not in st.session_state:
    st.session_state["terms_by_file"] = {}

# --- Generate AI terms ---
st.subheader("1️⃣ Generate O-1 highlight phrases (AI)")

if st.button("Generate phrases for all PDFs", type="primary"):
    with st.spinner("Analyzing PDFs with AI…"):
        for f in uploaded_files:
            text = extract_text_from_pdf_bytes(f.getvalue())
            data = suggest_ovisa_terms(text)
            st.session_state["terms_by_file"][f.name] = data
    st.success("Done. Review or edit phrases below.")

st.divider()

# --- Per-PDF review + annotation ---
st.subheader("2️⃣ Review phrases and generate annotated PDFs")

for f in uploaded_files:
    st.markdown(f"### 📄 {f.name}")

    data = st.session_state["terms_by_file"].get(f.name, {"terms": [], "rationale_tags": {}})
    terms = data.get("terms", [])

    edited_terms_text = st.text_area(
        "Highlight phrases (one per line)",
        value="\n".join(terms),
        height=180,
        key=f"terms_{f.name}",
    )

    edited_terms = [t.strip() for t in edited_terms_text.splitlines() if t.strip()]

    with st.expander("Show AI rationale tags"):
        st.json(data.get("rationale_tags", {}))

    if st.button(f"Generate annotated PDF for {f.name}", key=f"annotate_{f.name}"):
        with st.spinner("Annotating PDF…"):
            output_bytes, report = highlight_terms_in_pdf_bytes(
                f.getvalue(), edited_terms
            )

        output_name = f.name.replace(".pdf", "_highlighted.pdf")

        st.success(f"Annotated PDF created — {report['total_hits']} highlights found")

        st.download_button(
            label="⬇️ Download annotated PDF",
            data=output_bytes,
            file_name=output_name,
            mime="application/pdf",
        )

st.divider()
st.caption("O-1 PDF Highlighter • Streamlit + OpenAI + PyMuPDF")
