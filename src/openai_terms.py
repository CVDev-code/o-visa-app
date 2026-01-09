import json
import os
from openai import OpenAI

from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


def _get_secret(name: str):
    """
    Works on Streamlit Cloud (st.secrets) and locally (.env / env vars).
    """
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name)


def suggest_ovisa_terms(document_text: str, feedback: dict | None = None) -> dict:
    """
    Calls OpenAI to extract O-1-relevant highlight phrases.
    feedback (optional) structure:
      {
        "approved_examples": ["...","..."],
        "rejected_examples": ["...","..."]
      }
    Returns: {"terms": [...], "rationale_tags": {...}}
    """
    api_key = _get_secret("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    model = _get_secret("OPENAI_MODEL") or "gpt-4.1-mini"
    client = OpenAI(api_key=api_key)

    approved = (feedback or {}).get("approved_examples", [])
    rejected = (feedback or {}).get("rejected_examples", [])

    # Always supply these placeholders to avoid KeyError if the template contains them.
    prompt = USER_PROMPT_TEMPLATE.format(
        text=document_text,
        approved_examples="\n".join(approved) if approved else "None",
        rejected_examples="\n".join(rejected) if rejected else "None",
    )

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw_output = response.output_text

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"OpenAI returned invalid JSON:\n{raw_output}") from e

    # Normalise output
    terms = data.get("terms", [])
    data["terms"] = [t.strip() for t in terms if isinstance(t, str) and t.strip()]

    if "rationale_tags" not in data or not isinstance(data["rationale_tags"], dict):
        data["rationale_tags"] = {}

    return data
