import json
from retrieval_system.preprocessing.pipeline import QueryPipeline

pipeline = QueryPipeline("data/jargon_iiti.json")

with open("tests/test_queries.json") as f:
    tests = json.load(f)

for t in tests:
    result = pipeline.process(t["query"])

    print("\n" + "="*50)
    print("QUERY:", result["original"])
    print("EXPANDED:", result["expanded"])
    print("MULTI:", result["multi_queries"])