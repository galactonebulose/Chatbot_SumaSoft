from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.schemas import ResourceModel

from app.services.parsers import parse_pdf, parse_docx, parse_csv, parse_txt, chunk_text
from app.services.vector_store import upsert_chunks, query_vector_store
from app.services.connectors import sync_local_directory, sync_mongodb, sync_postgresql, sync_api_endpoint

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    top_k: int = 3

class ConnectorSyncRequest(BaseModel):
    type: str # 'directory', 'mongodb', 'postgresql', 'api'
    config: Dict[str, Any]
    user_id: Optional[int] = None

@router.post("/upload")
async def upload_resource(
    file: UploadFile = File(...),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Upload a document (PDF, DOCX, CSV, TXT), chunk it, embed it, index in Qdrant, and save in PostgreSQL"""
    filename = file.filename
    ext = filename.split(".")[-1].lower()
    
    if ext not in ["pdf", "docx", "csv", "txt"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: '.{ext}'")
        
    try:
        content = await file.read()
        
        if ext == "pdf":
            text_content = parse_pdf(content)
        elif ext == "docx":
            text_content = parse_docx(content)
        elif ext == "csv":
            text_content = parse_csv(content)
        else: # txt
            text_content = parse_txt(content)
            
        chunks = chunk_text(text_content)
        if not chunks:
            return {"filename": filename, "status": "empty", "chunks_indexed": 0}
            
        metadatas = [{
            "source": "upload",
            "filename": filename,
            "chunk_index": i
        } for i in range(len(chunks))]
        
        await upsert_chunks(chunks, metadatas)
        
        # Save resource details in PostgreSQL database
        try:
            new_res = ResourceModel(
                filename=filename,
                type=ext,
                size=len(content),
                status="processed",
                user_id=user_id
            )
            db.add(new_res)
            db.commit()
        except Exception as db_err:
            db.rollback()
            print(f"Warning: Failed to save uploaded resource metadata to Postgres: {db_err}")
            
        return {"filename": filename, "status": "success", "chunks_indexed": len(chunks)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {str(e)}")

@router.post("/connector/sync")
async def sync_connector(request: ConnectorSyncRequest):
    """Trigger a synchronization job for a configured data connector"""
    conn_type = request.type.lower()
    cfg = request.config
    
    try:
        if conn_type == "directory":
            path = cfg.get("path")
            if not path:
                raise HTTPException(status_code=400, detail="Missing required config key: 'path'")
            result = await sync_local_directory(path, request.user_id)
            
        elif conn_type == "mongodb":
            url = cfg.get("mongo_url")
            db = cfg.get("db_name")
            col = cfg.get("collection_name")
            fields = cfg.get("fields", [])
            if not all([url, db, col, fields]):
                raise HTTPException(status_code=400, detail="Missing MongoDB configurations: 'mongo_url', 'db_name', 'collection_name', 'fields'")
            result = await sync_mongodb(url, db, col, fields, request.user_id)
            
        elif conn_type == "postgresql":
            url = cfg.get("postgres_url")
            table = cfg.get("table_name")
            columns = cfg.get("columns", [])
            if not all([url, table, columns]):
                raise HTTPException(status_code=400, detail="Missing PostgreSQL configurations: 'postgres_url', 'table_name', 'columns'")
            result = await sync_postgresql(url, table, columns, request.user_id)
            
        elif conn_type == "api":
            url = cfg.get("url")
            method = cfg.get("method", "GET")
            headers = cfg.get("headers", {})
            path = cfg.get("fields_path")
            if not url:
                raise HTTPException(status_code=400, detail="Missing API URL config key: 'url'")
            result = await sync_api_endpoint(url, method, headers, path, request.user_id)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported connector type: '{conn_type}'")
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connector synchronization failed: {str(e)}")

@router.post("/search")
async def search_resources(request: SearchRequest):
    """Query the Qdrant index to retrieve semantic match snippets"""
    try:
        results = await query_vector_store(request.query, top_k=request.top_k)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge search failed: {str(e)}")

@router.get("/")
async def list_resources(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all ingested resources, optionally filtered by user_id"""
    try:
        query = db.query(ResourceModel)
        if user_id is not None:
            query = query.filter(ResourceModel.user_id == user_id)
        resources = query.all()
        return [
            {
                "id": r.id,
                "filename": r.filename,
                "filepath": r.filepath,
                "type": r.type,
                "size": r.size,
                "status": r.status,
                "created_at": r.created_at,
                "user_id": r.user_id
            }
            for r in resources
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list resources: {str(e)}")

@router.delete("/{resource_id}")
async def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    """Delete a resource metadata from PostgreSQL and clean up its indexed chunks in Qdrant"""
    res = db.query(ResourceModel).filter(ResourceModel.id == resource_id).first()
    if not res:
        raise HTTPException(status_code=404, detail=f"Resource with ID {resource_id} not found")
        
    try:
        # Delete from Qdrant
        from app.core.db import get_qdrant_client
        from qdrant_client.http import models as qmodels
        
        q_client = get_qdrant_client()
        try:
            q_client.delete(
                collection_name="knowledge_base",
                points_selector=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="metadata.filename",
                            match=qmodels.MatchValue(value=res.filename)
                        )
                    ]
                )
            )
        except Exception as q_err:
            print(f"Warning: Failed to delete Qdrant vectors for resource {res.filename}: {q_err}")
            
        # Delete from DB
        db.delete(res)
        db.commit()
        return {"status": "success", "message": f"Resource {resource_id} and its vector chunks deleted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete resource: {str(e)}")