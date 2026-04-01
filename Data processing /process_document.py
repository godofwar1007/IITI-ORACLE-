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
from langchain_core.documents import Document

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
    
splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=128,
    separators=["\n\n", "\n", " ", ""]
)  

def clean_text(text: str) -> str:
   
    text = re.sub(r'<[^>]+>', '', text)  # removing the html tags 
       
    text = html.unescape(text)  # Decode HTML entities (e.g., &amp; -> &, &nbsp; -> space)
    
    text = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', text)  # removing markdown image syntax ![alt](url)
    
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # removing markdown links [text](url) but keep the text
    
    text = re.sub(r'\s+', ' ', text).strip() # replaicing any whitespace with a single space 
    
    return text

    
for doc in pages_collection.find({}):

    doc_id = str(doc["_id"])
    url = doc.get("url", "")
    title = doc.get("title", "")
    content = doc.get("content", "")
    last_crawled = doc.get("last_crawled")    

    cleaned_text = clean_text(content)
    if not cleaned_text:
        continue         # step to skip empty documents . dunno if it helps yet 

    # the metadata

    metadata = {
        "document_id" : doc_id,
        "url" : url,
        "title" : title,
        "last_crawled" : str(last_crawled) if last_crawled else None,
    } 

    # merging any metadata from the metadata field of the doc 
    extra = doc.get("metadata",{})
    for k,v in extra.items():
        if k not in metadata:
            metadata[k] = v

    langchain_doc = Document(page_content=cleaned_text, metadata=metadata)

    chunks = splitter.split_documents([langchain_doc])        
