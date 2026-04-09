from crewai_tools import tool
from crewai import Agent , Task , Crew ,Process , LLM

from  pymongo import MongoClient
import os
from dotenv import load_dotenv
from crewai_tools import ScrapeWebsiteTool , SerperDevTool
load_dotenv()



client  = MongoClient(os.environ.get("MONGODB_URI"))

@tool("Mongo DB search Tool")
def mongodbsearchtool(query : str) -> str :
                collection = client["IITI_BOT"]
                database = collection["scraped_pages"]

                results = database.find({"$text" : {"$search" : query}}).limit(3)

                output = []

                for docs in results:
                    str_docs = str(docs)
                    output.append(str_docs[:1500] + " Truncated ...")
                return "\n".join(output) if output else "No relevant details found"
web_tool = ScrapeWebsiteTool()
search_tool = SerperDevTool()
llm = LLM(model="groq/model_name" , temperature = 0.7 , api_key = os.environ.get("GROQ_API_KEY"))

class Agentic_System():
        def proceed(self , user_query):
            retriever_agent = Agent( role = "Lead Data Retriever",
                                    goal='Intelligently navigate databases, follow URLs found in database text, and extract raw data.',
                                    backstory = (
                                        'You are a master data miner.'
                                        'CRITICAL RULE: When you search the MongoDB database and find markdown links like [text](url), '
                                        'you MUST NOT just give the URL to the user. You must extract the URL and use the ScrapeWebsiteTool '
                                        'and retrieve the actual data from it to answer the query.'),
                
                                    tools = [web_tool , search_tool ,mongodbsearchtool] ,
                                    llm = llm,
                                    verbose = False )
            sale_agent = Agent(role='Information Processor',
                                    goal='Draft a clean, professional, and comprehensive final response based on the matched data.' , 
                                backstory='You are a skilled communicator. You take raw facts and turn them into easy-to-understand, perfectly formatted answers.',
                                    # tools = [web_tool , search_tool ,mongodbsearchtool]
                                    llm = llm,verbose = False)
            match_agent = Agent(role = 'Data Matcher and Analyzer',
                                    goal ='Analyze the raw data retrieved by the Retriever, filter out noise, and match the most relevant facts to the exact user query.',
                                    backstory = 'You are a highly analytical AI. You take messy data from multiple sources and find the exact needle in the haystack.',
                
                                    # tools = [web_tool , search_tool ,mongodbsearchtool]
                                    llm = llm,verbose = False)
            task_retrieve = Task(  description=(
        f'Retrieve all detailed information regarding this query: "{user_query}". \n'
        'Steps to follow:\n'
        '1. Query the MongoDB database first.\n'
        '2. IF the database returns markdown links containing the relevant information, YOU MUST use the ScrapeWebsiteTool  to visit those URLs and extract the actual data.\n'
        '3. If the database lacks info, use the Search Tool to find relevant college URLs, then use the Scrape tool on those URLs.\n'
       
          ),
    expected_output='A raw compilation of actual data (NOT just links) extracted from the database and  websites.',
    agent=retriever_agent)
            task_match = Task( description='Review the raw data provided by the Retriever. Filter out irrelevant information and strictly extract data answering the query.' ,
                              agent = match_agent ,  expected_output='A list of verified facts perfectly matched to the user query.',)
            task_sale = Task(description='Take the verified facts and write a final, polished answer for the user.' , agent = sale_agent ,
                             expected_output='A clean, well-formatted response addressing the user query. Do not invent any information.')

            ccrew = Crew (agents = [retriever_agent, match_agent , sale_agent] , tasks = [task_retrieve , task_match , task_sale] , process = Process.hierarchical , manager_llm = llm , verbose =True)

            result = ccrew.kickoff()
            return result

        
