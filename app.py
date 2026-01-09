import io
import zipfile
import streamlit as st
from dotenv import load_dotenv

from src.pdf_text import extract_text_from_pdf_bytes
from src.openai_terms import suggest_ovisa_quotes
from src.pdf_highlighter import highlight_terms_in_pdf_bytes
from src.prompts import CRITERIA

load_dotenv()
st.set_page_config(page_title="O-1 PDF Highlighter", layout="wide")

st.title("O-1 PDF Highlighter")
st.caption("Upload PDFs → choose criteria → approve/reject quotes → export criterion-specific highlighted PDFs")

# -------------------------
# Case setup (sidebar)
# -------------------------
with st.sidebar:
    st.header("Case setup")
    beneficiary_name = st.text_input("Beneficiary full name", value="")
    variants_raw = st.text_input("Name variants (comma-separated)", value="")
    beneficiary_variants = [v.strip() for v in variants_raw.split(",") if v.strip()]

    st.subheader("Select O-1 criteria to extract")
    default_criteria = ["2", "3", "4"]  # sensible defaults for musicians
    selected_criteria_ids = []
    for cid, desc in CRITERIA.items():
        checked = st.checkbox(f"({cid}) {desc}", value=(cid in default_criteria))
        if checked:
            selected_criteria_ids.append(cid)

    st.divider()
    st.caption("Tip: Tick only the criteria you want to build evidence for in this batch.")

uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Upload at least one PDF to begin.")
    st.stop()

if not beneficiary_name.strip():
    st.warning("Enter the beneficiary full name in the sidebar to improve extraction accuracy.")
    st.stop()

if not selected_criteria_ids:
    st.warning("Tick at least one O-1 criterion in the sidebar.")
    st.stop()

st.divider()

# -------------------------
# Session state
# -------------------------
if "ai_by_file" not in st.session_state:
    # filename -> {"by_criterion": {"1":[{"quote","strength"}]}, "notes": "..."}
    st.session_state["ai_by_file"] = {}

if "approval" not in st.session_state:
    # filename -> criterion -> quote -> True/False
    st.session_state["approval"] = {}

# -------------------------
# Step 1: Generate AI quotes
# -------------------------
st.subheader("1️⃣ Generate criterion-tagged quote candidates (AI)")

colA, colB, colC = st.columns([1, 1, 2])
with colA:
    run_ai = st.button("Generate for all PDFs", type="primary")
with colB:
    clear = st.button("Clear results")

if clear:
    st.session_state["ai_by_file"] = {}
    st.session_state["approval"] = {}
    st.success("Cleared AI results and approvals.")

if run_ai:
    with st.spinner("Reading PDFs and generating quote candidates…"):
        for f in uploaded_files:
            text = extract_text_from_pdf_bytes(f.getvalue())
            data = suggest_ovisa_quotes(
                document_text=text,
                beneficiary_name=beneficiary_name,
                beneficiary_variants=beneficiary_variants,
                selected_criteria_ids=selected_criteria_ids,
                feedback=None,
            )
            st.session_state["ai_by_file"][f.name] = data

            # Initialize approvals: approve everything initially
            if f.name not in st.session_state["approval"]:
                st.session_state["approval"][f.name] = {}
            for cid in selected_criteria_ids:
                items = data["by_criterion"].get(cid, [])
                st.session_state["approval"][f.name][cid] = {it["quote"]: True for it in items}

    st.success("Done. Review and approve/reject per criterion below.")

st.divider()

# -------------------------
# Step 2: Approve/Reject (per PDF, per criterion)
# -------------------------
st.subheader("2️⃣ Approve / Reject quotes by criterion")

for f in uploaded_files:
    st.markdown(f"## 📄 {f.name}")

    data = st.session_state["ai_by_file"].get(f.name)
    if not data:
        st.info("No AI results yet for this PDF. Click “Generate for all PDFs”.")
        continue

    notes = data.get("notes", "")
    if notes:
        with st.expander("AI notes"):
            st.write(notes)

    by_criterion = data.get("by_criterion", {})

    # Regenerate with feedback (per PDF) – lightweight steering
    regen_col1, regen_col2 = st.columns([1, 3])
    with regen_col1:
        regen_btn = st.button("Regenerate with my feedback", key=f"regen_{f.name}")
    with regen_col2:
        st.caption("Tip: Reject weak quotes, then regenerate to tighten results for this PDF.")

    if regen_btn:
        # Build compact feedback examples across selected criteria
        approved_examples = []
        rejected_examples = []
        for cid in selected_criteria_ids:
            approvals = st.session_state["approval"].get(f.name, {}).get(cid, {})
            for q, ok in approvals.items():
                (approved_examples if ok else rejected_examples).append(q)
        feedback = {
            "approved_examples": approved_examples[:15],
            "rejected_examples": rejected_examples[:15],
        }
        with st.spinner("Regenerating with feedback…"):
            text = extract_text_from_pdf_bytes(f.getvalue())
            new_data = suggest_ovisa_quotes(
                document_text=text,
                beneficiary_name=beneficiary_name,
                beneficiary_variants=beneficiary_variants,
                selected_criteria_ids=selected_criteria_ids,
                feedback=feedback,
            )
        st.session_state["ai_by_file"][f.name] = new_data
        # reset approvals to True for new candidates
        st.session_state["approval"][f.name] = {}
        for cid in selected_criteria_ids:
            items = new_data["by_criterion"].get(cid, [])
            st.session_state["approval"][f.name][cid] = {it["quote"]: True for it in items}
        st.success("Regenerated. Review the updated lists below.")
        st.rerun()

    for cid in selected_criteria_ids:
        crit_title = f"Criterion ({cid})"
        crit_desc = CRITERIA.get(cid, "")
        items = by_criterion.get(cid, [])

        with st.expander(f"{crit_title}: {crit_desc}", expanded=(cid in {"2","3","4"})):
            if not items:
                st.write("No candidates found for this criterion in this document.")
                continue

            # bulk actions
            b1, b2, b3 = st.columns([1, 1, 2])
            with b1:
                if st.button("Approve all", key=f"approve_all_{f.name}_{cid}"):
                    st.session_state["approval"][f.name][cid] = {it["quote"]: True for it in items}
            with b2:
                if st.button("Reject all", key=f"reject_all_{f.name}_{cid}"):
                    st.session_state["approval"][f.name][cid] = {it["quote"]: False for it in items}

            approvals = st.session_state["approval"].get(f.name, {}).get(cid, {})

            for i, it in enumerate(items):
                q = it["quote"]
                strength = it.get("strength", "medium")
                label = f"[{strength}] {q}"
                approvals[q] = st.checkbox(
                    label,
                    value=approvals.get(q, True),
                    key=f"chk_{f.name}_{cid}_{i}",
                )

            st.session_state["approval"][f.name][cid] = approvals

            approved = [q for q, ok in approvals.items() if ok]
            rejected = [q for q, ok in approvals.items() if not ok]
            st.write(f"✅ Approved: **{len(approved)}** | ❌ Rejected: **{len(rejected)}**")

st.divider()

# -------------------------
# Step 3: Export one PDF per criterion (and ZIP)
# -------------------------
st.subheader("3️⃣ Export highlighted PDFs by criterion")

def build_highlighted_pdf_bytes(pdf_bytes: bytes, quotes: list[str]):
    # reuses your red-box highlighter; report contains total hits
    return highlight_terms_in_pdf_bytes(pdf_bytes, quotes)

# Single-file, per-criterion export buttons + "Export all as ZIP"
zip_btn = st.button("Export ALL selected criteria as ZIP (all PDFs)", type="primary")

zip_buffer = None
if zip_btn:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in uploaded_files:
            data = st.session_state["ai_by_file"].get(f.name)
            if not data:
                continue
            for cid in selected_criteria_ids:
                approvals = st.session_state["approval"].get(f.name, {}).get(cid, {})
                approved_quotes = [q for q, ok in approvals.items() if ok]
                if not approved_quotes:
                    continue
                out_bytes, report = build_highlighted_pdf_bytes(f.getvalue(), approved_quotes)
                out_name = f.name.replace(".pdf", f"_criterion-{cid}_highlighted.pdf")
                zf.writestr(out_name, out_bytes)
    zip_buffer.seek(0)

if zip_buffer:
    st.download_button(
        "⬇️ Download ZIP",
        data=zip_buffer.getvalue(),
        file_name="o1_criterion_highlighted_pdfs.zip",
        mime="application/zip",
    )

st.caption("You can also export per PDF/per criterion below:")

for f in uploaded_files:
    data = st.session_state["ai_by_file"].get(f.name)
    if not data:
        continue

    st.markdown(f"### 📄 {f.name}")

    for cid in selected_criteria_ids:
        approvals = st.session_state["approval"].get(f.name, {}).get(cid, {})
        approved_quotes = [q for q, ok in approvals.items() if ok]
        if not approved_quotes:
            continue

        if st.button(f"Generate PDF for Criterion {cid}", key=f"gen_{f.name}_{cid}"):
            with st.spinner("Annotating…"):
                out_bytes, report = build_highlighted_pdf_bytes(f.getvalue(), approved_quotes)
            out_name = f.name.replace(".pdf", f"_criterion-{cid}_highlighted.pdf")
            st.success(f"Created {out_name} — {report.get('total_hits', 0)} highlights found")
            st.download_button(
                f"⬇️ Download {out_name}",
                data=out_bytes,
                file_name=out_name,
                mime="application/pdf",
                key=f"dl_{f.name}_{cid}",
            )

st.divider()
st.caption("O-1 PDF Highlighter • Criterion-based extraction + approval workflow + per-criterion exports")
