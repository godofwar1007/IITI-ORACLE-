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

model_name = "BAAI/bge-m3"
model = SentenceTransformer(model_name)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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


# here we make a file named chunks.json1 just to write and debug the whole thing cz we havent setup the vector db yet once it is set then we will insert the chunks dynamically directly into the vector db     
with open("chunks.jsonl", "w", encoding="utf-8") as f:
    
   #for doc in pages_collection.find({}).limit(10):  -> used this line to test and make a chunks.json
    for doc in pages_collection.find({}):
        
        try:
            
            doc_id = str(doc["_id"])
            url = doc.get("url", "")
            title = doc.get("title", "")
            content = doc.get("content", "")
            last_crawled = doc.get("last_crawled")

            cleaned_text = clean_text(content)
            if not cleaned_text:
                continue

            metadata = {
                "document_id": doc_id,
                "url": url,
                "title": title,
                "last_crawled": str(last_crawled) if last_crawled else None,
            }
           
            extra = doc.get("metadata", {})
            for k, v in extra.items():
                if k not in metadata:
                    metadata[k] = v

            langchain_doc = Document(page_content=cleaned_text, metadata=metadata)
            chunks = splitter.split_documents([langchain_doc])

            for idx, chunk in enumerate(chunks):

                embedding = model.encode(chunk.page_content, normalize_embeddings=True).tolist()
                
                chunk_dict = {
                    **chunk.metadata,
                    "chunk_index": idx,
                    "chunk_text": chunk.page_content,
                    "embedding": embedding
                }
                
                f.write(json.dumps(chunk_dict) + "\n")

            logging.info(f"Processed {doc_id} -> {len(chunks)} chunks")

        except Exception as e:
            logging.error(f"Error with document {doc_id}: {e}")
            continue

client.close()        
