import re


def clean(text, limit=200):
    """Strip markup and JSON/shell punctuation from free text (buyer, supplier, API errors).

    It does NOT stop plain-English instructions. The real wall is that agents can neither
    approve (only the owner's email can) nor pay (only `tick` can).
    """
    return re.sub(r"[^A-Za-z0-9 .,%$:()/_-]", "", str(text))[:limit]
