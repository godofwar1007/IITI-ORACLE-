import os
import json 
import logging 
import re
import html
from typing import  List,Dict,Any, Tuple

import pymongo
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer
from langchain_text_splitters import RecursiveCharacterTextSplitter

from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")  # just to check if the load_dotenv() is working properly 
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set")

client = pymongo.MongoClient(MONGO_URI)
db = client["IITI_BOT"]
pages_collection = db["scraped_pages"]

def get_document_by_url(url : str) -> dict:

    doc = pages_collection.find_one({"url": url})
    if doc:

        return{
            "url" : doc.get('url'),
            "title" : doc.get('title'),
            "content" : doc.get('content'),
            "last_crawled" : doc.get('last_crawled')
        }
    
for doc in pages_collection.find({}):
    doc_id = str(doc["_id"])
    url = doc.get("url", "")
    title = doc.get("title", "")
    content = doc.get("content", "")
    last_crawled = doc.get("last_crawled")    

def clean_text(text: str) -> str:

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    #  Decode HTML entities (e.g., &amp; -> &, &nbsp; -> space)
    text = html.unescape(text)
    
    # Remove markdown image syntax ![alt](url)
    text = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', text)
    
    # Remove markdown links [text](url) but keep the text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Normalize whitespace: replace any whitespace sequence with a single space
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


