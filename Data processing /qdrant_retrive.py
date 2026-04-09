import os 
from qdrant_client import QdrantClient,models
from qdrant_client.http.exceptions import UnexpectedResponse
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
import json 
from dotenv import load_dotenv
import uuid
from sentence_transformers import SentenceTransformer

load_dotenv()

BATCH_SIZE=67
NAMESPACE_UUID = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')

client = QdrantClient(url=URL, api_key=QDRANT_API_KEY)
collection_name = 'IITI_BOT'

encoder = SentenceTransformer("BAAI/bge-m3")


def retriver(query: str,limit: int = 20) -> list[models.ScoredPoint]:

    response = client.query_points(
        collection_name=collection_name,
        prefetch=[
            models.Prefetch(
                query=models.Document(
                    text=query,
                    model="Qdrant/bm25",
                ),
                using="sparse",
                limit=limit,
            ),

            models.Prefetch(
                query=encoder.encode(query,normalize_embeddings=True).tolist(),
                using="dense",
                limit=limit,
            )
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=limit  
    )

    return response.points

def reranker(chunks):
    # so this one is under dev i have ot yet made the logic and there is no personalization layer but i didnt wanna mess up with the architecture that i thought so just adding an empty function 
    return chunks


def retriver_reanker(query: str,top_k : int = 10) -> list[models.ScoredPoint]: 

    retrived = retriver(query)  # if u wanna tweak the no of chunks returned just past a limit as an argument here as of now or just tweak in the argument of the retriver_reranker function 
    reranked = reranker(retrived)

    return reranked[:top_k]
    
