import os
import httpx
from typing import List, Dict, Any
from pymongo import MongoClient
from sqlalchemy import create_engine, text

from app.services.parsers import parse_pdf, parse_docx, parse_csv, parse_txt, chunk_text
from app.services.vector_store import upsert_chunks

async def sync_local_directory(directory_path: str, user_id: int = None) -> Dict[str, Any]:
    """Scan a local directory and ingest supported documents (PDF, DOCX, CSV, TXT)"""
    if not os.path.exists(directory_path):
        raise ValueError(f"Directory path '{directory_path}' does not exist.")
        
    files_processed = 0
    total_chunks = 0
    
    for filename in os.listdir(directory_path):
        filepath = os.path.join(directory_path, filename)
        if not os.path.isfile(filepath):
            continue
            
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".docx", ".csv", ".txt"]:
            continue
            
        try:
            with open(filepath, "rb") as f:
                content = f.read()
                
            if ext == ".pdf":
                text_content = parse_pdf(content)
            elif ext == ".docx":
                text_content = parse_docx(content)
            elif ext == ".csv":
                text_content = parse_csv(content)
            else: # .txt
                text_content = parse_txt(content)
                
            chunks = chunk_text(text_content)
            if not chunks:
                continue
                
            metadatas = [{
                "source": "local_directory",
                "filename": filename,
                "filepath": filepath,
                "chunk_index": i
            } for i in range(len(chunks))]
            
            await upsert_chunks(chunks, metadatas)
            files_processed += 1
            total_chunks += len(chunks)
            
            # Save Resource details in Postgres
            try:
                from app.core.db import SessionLocal
                from app.models.schemas import ResourceModel
                
                db = SessionLocal()
                new_res = ResourceModel(
                    filename=filename,
                    filepath=filepath,
                    type=ext.replace(".", ""),
                    size=len(content),
                    status="processed",
                    user_id=user_id
                )
                db.add(new_res)
                db.commit()
                db.close()
            except Exception as db_err:
                print(f"Failed to save resource record in Postgres for {filename}: {db_err}")
                
        except Exception as e:
            print(f"Failed to ingest file '{filename}': {e}")
            
    return {"status": "success", "files_processed": files_processed, "total_chunks": total_chunks}

async def sync_mongodb(mongo_url: str, db_name: str, collection_name: str, fields_to_ingest: List[str], user_id: int = None) -> Dict[str, Any]:
    """Ingest fields from MongoDB documents in a collection"""
    client = MongoClient(mongo_url)
    db = client[db_name]
    col = db[collection_name]
    
    docs = list(col.find({}))
    if not docs:
        return {"status": "success", "message": "No documents found in collection"}
        
    all_chunks = []
    all_metadatas = []
    
    for doc in docs:
        doc_id = str(doc.get("_id"))
        doc_text_parts = []
        for field in fields_to_ingest:
            val = doc.get(field)
            if val:
                doc_text_parts.append(f"{field}: {val}")
                
        text_content = "\n".join(doc_text_parts)
        if not text_content.strip():
            continue
            
        chunks = chunk_text(text_content)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadatas.append({
                "source": "mongodb",
                "mongodb_url": mongo_url,
                "db_name": db_name,
                "collection": collection_name,
                "document_id": doc_id,
                "chunk_index": i
            })
            
    if all_chunks:
        await upsert_chunks(all_chunks, all_metadatas)
        # Create resource record
        try:
            from app.core.db import SessionLocal
            from app.models.schemas import ResourceModel
            db = SessionLocal()
            new_res = ResourceModel(
                filename=f"{db_name}.{collection_name}",
                filepath=mongo_url,
                type="mongodb",
                size=None,
                status="processed",
                user_id=user_id
            )
            db.add(new_res)
            db.commit()
            db.close()
        except Exception as db_err:
            print(f"Failed to save mongodb resource record: {db_err}")
        
    return {"status": "success", "documents_processed": len(docs), "total_chunks": len(all_chunks)}

async def sync_postgresql(postgres_url: str, table_name: str, columns_to_ingest: List[str], user_id: int = None) -> Dict[str, Any]:
    """Ingest rows from a PostgreSQL table"""
    engine = create_engine(postgres_url)
    
    query = text(f"SELECT * FROM {table_name}")
    all_chunks = []
    all_metadatas = []
    rows_count = 0
    
    with engine.connect() as connection:
        result = connection.execute(query)
        # Fetch columns indices
        keys = list(result.keys())
        
        for row in result:
            rows_count += 1
            row_dict = dict(zip(keys, row))
            row_text_parts = []
            
            for col in columns_to_ingest:
                if col in row_dict and row_dict[col] is not None:
                    row_text_parts.append(f"{col}: {row_dict[col]}")
                    
            text_content = "\n".join(row_text_parts)
            if not text_content.strip():
                continue
                
            chunks = chunk_text(text_content)
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadatas.append({
                    "source": "postgresql",
                    "table_name": table_name,
                    "row_index": rows_count,
                    "chunk_index": i
                })
                
    if all_chunks:
        await upsert_chunks(all_chunks, all_metadatas)
        # Create resource record
        try:
            from app.core.db import SessionLocal
            from app.models.schemas import ResourceModel
            db = SessionLocal()
            new_res = ResourceModel(
                filename=table_name,
                filepath=postgres_url,
                type="postgresql",
                size=None,
                status="processed",
                user_id=user_id
            )
            db.add(new_res)
            db.commit()
            db.close()
        except Exception as db_err:
            print(f"Failed to save postgresql resource record: {db_err}")
        
    return {"status": "success", "rows_processed": rows_count, "total_chunks": len(all_chunks)}

async def sync_api_endpoint(url: str, method: str = "GET", headers: Dict[str, Any] = None, fields_path: str = None, user_id: int = None) -> Dict[str, Any]:
    """Ingest JSON response payload from a web API endpoint"""
    headers = headers or {}
    method = method.upper()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            response = await client.get(url, headers=headers)
        else:
            response = await client.post(url, json={}, headers=headers)
            
        if response.status_code != 200:
            raise Exception(f"API Sync failed with status {response.status_code}: {response.text}")
            
        data = response.json()
        
    # Standardize data to a list of records
    records = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        # If fields_path is supplied, extract sublist
        if fields_path and fields_path in data:
            val = data[fields_path]
            if isinstance(val, list):
                records = val
            else:
                records = [val]
        else:
            records = [data]
            
    all_chunks = []
    all_metadatas = []
    
    for i, record in enumerate(records):
        # Format record
        record_text_parts = []
        if isinstance(record, dict):
            for k, v in record.items():
                if isinstance(v, (str, int, float, bool)):
                    record_text_parts.append(f"{k}: {v}")
        else:
            record_text_parts.append(str(record))
            
        text_content = "\n".join(record_text_parts)
        if not text_content.strip():
            continue
            
        chunks = chunk_text(text_content)
        for c_idx, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadatas.append({
                "source": "api_endpoint",
                "api_url": url,
                "record_index": i,
                "chunk_index": c_idx
            })
            
    if all_chunks:
        await upsert_chunks(all_chunks, all_metadatas)
        # Create resource record
        try:
            from app.core.db import SessionLocal
            from app.models.schemas import ResourceModel
            db = SessionLocal()
            new_res = ResourceModel(
                filename=url.split("/")[-1] or "api_endpoint",
                filepath=url,
                type="api",
                size=None,
                status="processed",
                user_id=user_id
            )
            db.add(new_res)
            db.commit()
            db.close()
        except Exception as db_err:
            print(f"Failed to save api resource record: {db_err}")
        
    return {"status": "success", "records_processed": len(records), "total_chunks": len(all_chunks)}
