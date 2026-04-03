import re


def clean_text(text: str) -> str:
    """
    Cleaning layer for query preprocessing.

    Handles:
    - Lowercasing
    - Removing special characters (except useful ones like / for courses)
    - Removing brackets content
    - Normalizing spaces
    - Keeping query semantics intact (IMPORTANT for RAG)
    
    """

    if not text:
        return ""

    text = text.lower()

    text = re.sub(r"\(.*?\)", "", text)

    text = re.sub(r"[-_,]", " ", text)

    text = re.sub(r"[^a-z0-9/\s]", " ", text)

    text = re.sub(r"\s+", " ", text).strip()

    return text

