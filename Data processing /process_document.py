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
# this os.getenv thing is not working on my setup so i hardcoded this 
# MONGO_URI = os.getenv("MONGO_URI")  # just to check if the load_dotenv() is working properly 
# if not MONGO_URI:
#     raise ValueError("MONGO_URI environment variable not set")

MONGO_URI = MONGO_URI

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

            metadata["source"] = "web"   # you can later detect PDFs from URL if needed

            is_official = False   # i guess this is the only way i can think for the official thingy as of now 
            if "official" in url.lower() or "notice" in url.lower() or "official" in title.lower():
                is_official = True
                metadata["official"] = is_official

            dept_map = {   # just a dept map to help get the dept 
                
                "cse": "CS",
                "computer science": "CS",
                "computer science and engineering": "CS",
                "CS": "CS",

                "mech": "ME",
                "mechanical": "ME",
                "mechanical engineering": "ME",
                "ME": "ME",
                
                "civil": "CE",
                "civil engineering": "CE",
                "ce": "CE",
                "CE": "CE",

                "ee": "EE",
                "electrical": "EE",
                "electrical engineering": "EE",
                "EE": "EE",

                "maths": "MNC",
                "mathematics": "MNC",
                "mathematics and computing": "MNC",
                "mnc": "MNC",
                "MNC": "MNC",

                "chemical": "CHE",
                "chemical engineering": "CHE",
                "CHE": "CHE",

                "space": "SSE",
                "space science": "SSE",
                "space engineering": "SSE",
                "sse": "SSE",
                "AA" : "SSE",
                "astronomy" : "SSE",

                "metallurgy": "MEMS",
                "material science": "MEMS",
                "metallurgy and material science": "MEMS",
                "MEMS": "MEMS",

            }

            found_dept = "ALL"
            lower_url = url.lower()    # incase if the dept is in url or title 
            lower_title = title.lower()
            for key, dept in dept_map.items():
                if key in lower_url or key in lower_title:
                    found_dept = dept
                    break
            metadata["department"] = found_dept   # 

            topic_map = {    # topic map as of now .... subject to change hopefully 
                "admission": "admission",
                "exam": "exam",
                "placement": "placement",
                "event": "event",
                "research": "research",
                "seminar": "event",
                "workshop": "event",
                "scholarship": "admission"
            }

            # same thing as i did for the dept 
            found_topic = "general"
            for key, topic in topic_map.items():
                if key in lower_url or key in lower_title:
                    found_topic = topic
                    break
            metadata["topic"] = found_topic

           # categorization based on the url 
            if "syllabus" in lower_url or "syllabus" in lower_title:  
                metadata["category"] = "syllabus"
            elif "faq" in lower_url or "faq" in lower_title:
                metadata["category"] = "faq"
            elif "timetable" in lower_url or "timetable" in lower_title:
                metadata["category"] = "timetable" 
            elif "policy" in lower_url or "policy" in lower_title:
                metadata["category"] = "policy"
            else:
                metadata["category"] = "general"   # appropriate default i guess

            # course_code (extract pattern like CS101, MA201 from title)
            course_match = re.search(r'\b([A-Z]{2,4}\d{3,4})\b', title)
            metadata["course_code"] = course_match.group(1) if course_match else None

            # tags just made this idk maybe will be filled later 
            metadata["tags"] = []

            metadata["last_updated"] = metadata["last_crawled"]   # 
           
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
