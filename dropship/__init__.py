import re


def clean(text, limit=200):
    """Defang free text (buyer, supplier, API errors) before it reaches an agent's eyes."""
    return re.sub(r"[^A-Za-z0-9 .,%$:()/_-]", "", str(text))[:limit]
