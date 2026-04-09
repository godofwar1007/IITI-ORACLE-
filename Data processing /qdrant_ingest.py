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

load_dotenv()

BATCH_SIZE=67
NAMESPACE_UUID = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')

client = QdrantClient(url=URL, api_key=API_KEY)
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


def scalar_quantization():

    collection_info=client.get_collection(collection_name)
    if collection_info.quantization_config is None:
        client.update_collection(
            collection_name=collection_name,
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True
                ),
            ),
        )
        print("Enabled scalar quantization (INT8) on collection")

    else:
        print("Quantization already configured - skipping")    


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
    category: str = "general"    # changed to match process_document.py
    last_updated: str            
    embedding: List[float]       # the vector 
    tags: List[str] = []         # added missing field

    @field_validator('topic')
    def valid_topic(cls, v):
        allowed = {"admission", "exam", "placement", "event", "research", "general"}
        if v not in allowed:
            return "general"     # default 
        return v

    @field_validator('category')
    def valid_category(cls, v):
        allowed = {"notice", "syllabus", "timetable", "faq", "policy", "general"}
        if v not in allowed:
            return "general"     # default changed to general
        return v
    

def create_payload_indexes():
    # Get existing indexes to avoid duplicates (idempotent)
    collection_info = client.get_collection(collection_name)  
    existing_schema = collection_info.payload_schema or {}
    existing_fields = set(existing_schema.keys())

    # Keyword indexes
    keyword_fields = ["document_id", "source", "department", "course_code", "topic", "category"]
    for field in keyword_fields:
        if field not in existing_fields:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=models.KeywordIndexParams(
                    type="keyword",
                    on_disk=False,
                    is_tenant=(field == "department")
                )
            )
            print(f"Created keyword index on '{field}'")
        else:
            print(f"Index on '{field}' already exists – skipping")

    # boolean index
    if "official" not in existing_fields:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="official",
            field_schema=models.BoolIndexParams(type="bool")
        )
        print("Created boolean index on 'official'")
    else:
        print("Index on 'official' already exists – skipping")

    # Integer index for chunk_index
    if "chunk_index" not in existing_fields:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="chunk_index",
            field_schema=models.IntegerIndexParams(type="integer")
        )
        print("Created integer index on 'chunk_index'")
    else:
        print("Index on 'chunk_index' already exists – skipping")
    
    # datetime one 
    if "last_updated" not in existing_fields:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="last_updated",
            field_schema=models.DatetimeIndexParams(type="datetime")
        )
        print("Created datetime index on 'last_updated'")
    else:
        print("Index on 'last_updated' already exists – skipping")

    # Array of keywords for tags
    if "tags" not in existing_fields:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="tags",
            field_schema=models.KeywordIndexParams(type="keyword", on_disk=False)
        )
        print("Created keyword array index on 'tags'")
    else:
        print("Index on 'tags' already exists – skipping")

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
                continue   # <-- added missing continue
            
            unique_id_str = f"{payload_obj.document_id}_{payload_obj.chunk_index}"
            point_id = str(uuid.uuid5(NAMESPACE_UUID,unique_id_str))         # creating a unique point id  

            point = models.PointStruct(
                id=point_id,
                vector={"dense":payload_obj.embedding},
                payload=payload_obj.model_dump(exclude={"embedding"})
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
                    points_batch = []   # clear batch to avoid infinite loop on persistent error

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
    scalar_quantization()
    create_payload_indexes()
    injest_chunks()
