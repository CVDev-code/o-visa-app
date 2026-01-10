import csv
import io
import re
from typing import Dict, Optional


URL_REGEX = re.compile(r"https?://\S+")
DATE_REGEX = re.compile(
    r"\b(?:\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{4}|\d{4})\b"
)
MONEY_REGEX = re.compile(r"\$\s?\d+(?:,\d{3})*(?:\.\d{2})?")


def extract_first_page_signals(text: str) -> Dict[str, Optional[str]]:
    """
    Lightweight heuristics for page-1 metadata detection.
    """
    return {
        "source_url": next(URL_REGEX.finditer(text), None).group(0)
        if URL_REGEX.search(text)
        else None,
        "performance_date": next(DATE_REGEX.finditer(text), None).group(0)
        if DATE_REGEX.search(text)
        else None,
        "salary_amount": next(MONEY_REGEX.finditer(text), None).group(0)
        if MONEY_REGEX.search(text)
        else None,
    }


def parse_metadata_csv(file_bytes: bytes) -> Dict[str, Dict[str, str]]:
    """
    CSV must contain a 'filename' column.
    Returns mapping: filename -> metadata dict
    """
    decoded = file_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))

    out = {}
    for row in reader:
        filename = row.get("filename")
        if not filename:
            continue
        out[filename] = {k: v for k, v in row.items() if v}
    return out


def merge_metadata(
    filename: str,
    auto: Dict[str, Optional[str]],
    global_defaults: Dict[str, Optional[str]],
    csv_data: Optional[Dict[str, Dict[str, str]]] = None,
    overrides: Optional[Dict[str, str]] = None,
) -> Dict[str, Optional[str]]:
    """
    Priority:
      1) Per-PDF overrides
      2) CSV row
      3) Global defaults
      4) Auto-detected
    """
    merged = dict(auto)

    if global_defaults:
        merged.update({k: v for k, v in global_defaults.items() if v})

    if csv_data and filename in csv_data:
        merged.update(csv_data[filename])

    if overrides:
        merged.update({k: v for k, v in overrides.items() if v})

    return merged
