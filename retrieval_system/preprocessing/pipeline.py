from retrieval_system.preprocessing.clean import clean_text
from retrieval_system.preprocessing.parser import parse_course_input
from retrieval_system.preprocessing.jargon_map import JargonMapper
from retrieval_system.preprocessing.query_expansion import QueryExpander
from retrieval_system.preprocessing.multi_query import GroqMultiQueryGenerator


class QueryPipeline:
    def __init__(self, jargon_path):

        self.mapper = JargonMapper(jargon_path)
        self.expander = QueryExpander(self.mapper)
        self.generator = GroqMultiQueryGenerator()

    def process(self, query: str):

        cleaned = clean_text(query)
        tokens = cleaned.split()

        course_info = parse_course_input(cleaned)

        expanded = self.expander.expand(tokens, course_info)

        multi_queries = self.generator.generate_queries(expanded)

        return {
            "original": query,
            "cleaned": cleaned,
            "courses": course_info["normalized_codes"],
            "expanded": expanded,
            "multi_queries": multi_queries
        }