
class QueryExpander:
    def __init__(self, jargon_mapper):
        self.mapper = jargon_mapper

    def expand(self, tokens: list, course_info: dict):
        """
        Clean expansion:
        - Keep original query structure
        - Add ONLY ONE expansion per jargon (in brackets)
        """

        expanded_tokens = []

        for token in tokens:
            key = token.lower()

            
            if key in self.mapper.jargon_map:
                entry = self.mapper.jargon_map[key]

                clean_expansion = entry["expansion"]

                expanded_tokens.append(
                    f"{token.upper()} ({clean_expansion})"
                )

            else:
                expanded_tokens.append(token.upper())


        if course_info and course_info.get("normalized_codes"):
            for code in course_info["normalized_codes"]:
                if code not in expanded_tokens:
                    expanded_tokens.append(code)

        return " ".join(expanded_tokens)