import os 
from qdrant_client import QdrantClient,models
from qdrant_client.http.exceptions import UnexpectedResponse
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
import json 
from dotenv import load_dotenv

load_dotenv()

BATCH_SIZE=67

client = QdrantClient(url="https://e81c49d4-abd1-4c97-a3fc-8acaed53060d.us-east-1-1.aws.cloud.qdrant.io:6333", api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MWQ0NzY1YzktMTlmZC00NjRkLWI1NTAtNTIzOWU2YjVmMTQ2In0.CyoZa5HJ9sctq0xw9VNROQbmDtHZ8BKZe9n_n26YRPs")
collection_name = 'IITI_BOT'

if not client.collection_exists(collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": models.VectorParams(
                size=1024,
                distance=models.Distance.COSINE
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(
                    on_disk=False
                )
            )
        }
    )
    print(f"Created collection '{collection_name}' with dense (1024, Cosine) and sparse vectors")
else:
    print(f"Collection '{collection_name}' already exists – keeping existing data")

class ChunkPayload(BaseModel):
    chunk_text: str
    chunk_index: int
    document_id: str
    url: Optional[str] = None
    title: Optional[str] = None
    source: str = "web"          # default
    official: bool = False       # default
    department: str = "ALL"
    course_code: Optional[str] = None
    topic: str = "general"
    category: str = "notice"
    last_updated: str            
    embedding: List[float]       # the vector 

    @field_validator('topic')
    def valid_topic(cls, v):
        allowed = {"admission", "exam", "placement", "event", "research", "general"}
        if v not in allowed:
            return "general"     # default 
        return v

    @field_validator('category')
    def valid_category(cls, v):
        allowed = {"notice", "syllabus", "timetable", "faq", "policy"}
        if v not in allowed:
            return "notice"
        return v
    

def create_payload_indexes():
    # Keyword indexes
    keyword_fields = ["document_id", "source", "department", "course_code", "topic", "category"]
    for field in keyword_fields:
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field,
            field_schema=models.KeywordIndexParams(
                type="keyword",
                on_disk=False,
                is_tenant=(field == "department")
            )
        )

        # boolean index
        client.create_payload_index(
            collection_name=collection_name,
            field_name="official",
            field_schema=models.BoolIndexParams(type="bool")
        )    

        # Integer index for chunk_index
        client.create_payload_index(
            collection_name=collection_name,
            field_name="chunk_index",
            field_schema=models.IntegerIndexParams(type="integer")
        )
        
        # datetime one 
        client.create_payload_index(
            collection_name=collection_name,
            field_name="last_updated",
            field_schema=models.DatetimeIndexParams(type="datetime")
        )

        # Array of keywords for tags
        client.create_payload_index(
            collection_name=collection_name,
            field_name="tags",
            field_schema=models.KeywordIndexParams(type="keyword", on_disk=False)
        )

def injest_chunks(jsonl_path="chunks.jsonl"):
    points_batch=[]
    total_points=0

    with open(jsonl_path,"r",encoding="utf-8") as f:
        for line_num,line in enumerate(f,1):
            line = line.strip()
            if not line:
                continue

            try:
                data=json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Line {line_num}: JSON decode error: {e}")
                continue

            if "last_updated" not in data and "last_crawled" in data:
                data["last_updated"] = data["last_crawled"]

            # validation using the pydantic we made 

            try:
                payload_obj = ChunkPayload(**data)
            except Exception as e:
                print(f"Line {line_num}: Validation failed: {e}")

            point_id = f"{payload_obj.document_id}_{payload_obj.chunk_index}"     # creating a unique point id  

            point = models.PointStruct(
                id=point_id,
                vector={"dense":payload_obj.embedding},
                payload=payload_obj.dict(exclude={"embedding"})
            )
            points_batch.append(point)          

            # here we just upsert when the batch is full .....subject to chanage 

            if len(points_batch) >= BATCH_SIZE:
                try:
                    client.upsert(collection_name=collection_name,points=points_batch)
                    total_points+=len(points_batch)
                    print(f"Upserted batch of {len(points_batch)} points (total: {total_points})")
                    points_batch=[]

                except Exception as e :
                    print(f"Upsert failed: {e}")

    # this one is for the final batch
    if points_batch:
        try:
            client.upsert(collection_name=collection_name,points=points_batch)
            total_points+=len(points_batch)
            print(f"Upserted final batch of {len(points_batch)} points (total: {total_points})")

        except Exception as e:
            print(f"Final upsert failed: {e}")

    print(f"Ingestion complete. Total points upserted: {total_points}")        



if __name__ == "__main__":
    create_payload_indexes()
    injest_chunks()    


