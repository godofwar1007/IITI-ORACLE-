import re

def parse_course_input(text: str):
    """
    Full parser for IIT course codes.
    
    Handles:
    - spaces (CS 204 → CS204)
    - variants (MA102N(A) → MA102)
    - cross-listed (CS204 / MA208)
    - noisy input ("cs-204 midsem lhc")
    - lowercase / mixed case
    """


    text = text.upper()

    text = re.sub(r"[,\-_/]", " ", text)


    text = re.sub(r"\(.*?\)", "", text)

    matches = re.findall(r"[A-Z]{2,3}\s?\d{2,3}", text)

    normalized_codes = []
    raw_codes = []

    for match in matches:
        raw = match.strip()


        norm = raw.replace(" ", "")

        raw_codes.append(raw)
        normalized_codes.append(norm)


    if len(normalized_codes) > 1:
        merged_key = "_".join(sorted(normalized_codes))
    else:
        merged_key = normalized_codes[0] if normalized_codes else None

    return {
        "input": text,
        "raw_codes": raw_codes,
        "normalized_codes": normalized_codes,
        "merged_key": merged_key
    }