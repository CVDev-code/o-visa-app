SYSTEM_PROMPT = """You are an expert US immigration paralegal specializing in USCIS O-1 (arts) petitions.
You extract short, high-signal phrases from press/reviews that help prove O-1 criteria.
Return ONLY valid JSON. No markdown. No commentary.
"""

USER_PROMPT_TEMPLATE = """
From the text below, extract a list of EXACT QUOTABLE PHRASES that are strong evidence for an O-1 (arts) petition.
Focus on phrases that show:
- critical acclaim / rave review language (e.g., "internationally acclaimed", "superb", "world-class")
- leading / starring / featured roles
- distinguished reputation of venues, festivals, orchestras, ensembles, conductors
- awards, nominations, prizes, competitions
- high salary / top-tier selection language (if present)
- "best of", "among the finest", "exceptional", "virtuosic", etc.

Rules:
- Return 8–35 phrases max (only include what exists).
- Each phrase should be an exact substring from the text (copy it verbatim).
- Prefer phrases between 5 and 30 words.
- Avoid duplicates and near-duplicates.
- Include the artist's name if it appears in the phrase.
- If the text is not in English, still extract exact phrases.

Return JSON in this shape:
{
  "terms": [ "phrase1", "phrase2", ... ],
  "rationale_tags": {
     "phrase1": ["critical_acclaim", "distinguished_venue"],
     "phrase2": ["award"]
  }
}

TEXT:
\"\"\"{text}\"\"\"
"""
