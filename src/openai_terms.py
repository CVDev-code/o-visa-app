import json
import os
from openai import OpenAI

from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

def suggest_ovisa_terms(document_text: str) -> dict:
    """
    Calls OpenAI to extract O-1-relevant highlight phrases.
    Returns a dict with keys: 'terms' and 'rationale_tags'.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=api_key)

    prompt = USER_PROMPT_TEMPLATE.format(text=document_text)

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
        raise RuntimeError(
            f"OpenAI returned invalid JSON:\n{raw_output}"
        ) from e

    # Normalise output
    terms = data.get("terms", [])
    data["terms"] = [t.strip() for t in terms if isinstance(t, str) and t.strip()]

    if "rationale_tags" not in data or not isinstance(data["rationale_tags"], dict):
        data["rationale_tags"] = {}

    return data
