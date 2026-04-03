import os
from groq import Groq


class GroqMultiQueryGenerator:
    def __init__(self):
        self.client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

    def generate_queries(self, query: str, num_queries: int = 4):
        

        prompt = f"""
You are an AI prompt (query) rewriting system for an IIT Indore assistant chatbot.
Your task is to given a human user query, generate {num_queries} different more enhanced search queries.

Do not invent new information or add new facts to the original query. The semantic mening must remain the same.
Rules:
- Keep meaning same
- Expand abbreviations (MSE → mid semester exam)
- Only Reformat/Paraphrase/Reaticuate the query to make more logical and sensible prompt.
- Be concise and diverse

Query: {query}

Return only a numbered list.
1.
2.
3.
4.

"""

        response = self.client.chat.completions.create(
            model="openai/gpt-oss-120b",  
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        text = response.choices[0].message.content

        # Parse numbered output
        queries = []
        for line in text.split("\n"):
            line = line.strip()
            if line and line[0].isdigit():
                queries.append(line.split(".", 1)[-1].strip())

        return queries
    
