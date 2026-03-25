from pymongo import MongoClient
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient,AsyncIOMotorCollection
import os 
from dotenv import load_dotenv
from fastapi import FastAPI , HTTPException , status , Depends
from pydantic import BaseModel
from typing import Optional,Dict
from datetime import datetime,timezone
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")  # just to check if the load_dotenv() is working properly 
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set")

now = datetime.now(timezone.utc)

client = AsyncIOMotorClient(os.getenv("MONGO_URI"))

db = client["IITI_BOT"]
pages_collection = db["scraped_pages"]

@asynccontextmanager
async def lifespan(app :FastAPI):
    # startup
    await pages_collection.create_index("url" , unique = True)
    yield
    if client is not None:
        # shutdown
        await client.close()

app = FastAPI(lifespan=lifespan)    


class ScrapedPage(BaseModel):
    url : str
    content : str
    title : Optional[str] = ""
    metadata : Optional[dict] = {}

# dependecy function 
def get_pages_collection()-> AsyncIOMotorCollection:
    return pages_collection     

@app.post("/store")
async def store_page(
    page : ScrapedPage,
    collection : AsyncIOMotorCollection = Depends(get_pages_collection)
): 
    """
    Store or update a scraped page in MongoDB.
    - If the URL already exists, update its content and metadata.
    - If it's a new URL, insert a new document.
    """

    try:

        update_page = {

            "$set" : {
                "content" : page.content,
                "title" : page.title,
                "metadata" : page.metadata,
                "last_crawled" : datetime.now(timezone.utc)
            },

            "$setOnInsert" : {
                "created_at" : datetime.now(timezone.utc)
            }
        }

        # do an upsert 
        result = await collection.update_one(
            {"url" : page.url},
            update_page,
            upsert=True
        )

        # it is just to check if the new document is created or not 
        if result.upserted_id:
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                "message": "Page created",
                "id": str(result.upserted_id),
                "url": page.url
            })
        else:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                "message": "Page updated",
                "url": page.url
            })

    except Exception as e :

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error : {e}"
        ) 




