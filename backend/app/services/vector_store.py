import httpx
import uuid
import json
from typing import List, Dict, Any, Optional
from qdrant_client.http import models as qmodels

from app.core.db import get_qdrant_client, SessionLocal
from app.models.schemas import LLMConfigModel
from app.core.config import settings

# Caching variables for local Ollama model detection
cached_ollama_model = None
last_check_time = 0
OLLAMA_CHECK_INTERVAL = 15  # seconds

async def get_ollama_model_cached() -> Optional[str]:
    """Retrieve active local Ollama models list and cache detection for robustness"""
    global cached_ollama_model, last_check_time
    import time
    
    current_time = time.time()
    if cached_ollama_model is not None and (current_time - last_check_time) < OLLAMA_CHECK_INTERVAL:
        return cached_ollama_model
        
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    emb_pref = getattr(settings, "DEFAULT_EMBEDDING_MODEL", "nomic-embed-text")
                    if emb_pref in models:
                        cached_ollama_model = emb_pref
                    elif f"{emb_pref}:latest" in models:
                        cached_ollama_model = f"{emb_pref}:latest"
                    else:
                        pref = settings.DEFAULT_MODEL_NAME
                        if pref in models:
                            cached_ollama_model = pref
                        elif f"{pref}:latest" in models:
                            cached_ollama_model = f"{pref}:latest"
                        else:
                            # Fallback to first pulled model (e.g. llama3.2:3b)
                            cached_ollama_model = models[0]
                    last_check_time = current_time
                    return cached_ollama_model
    except Exception as e:
        print(f"Ollama tags fetch failed: {e}")
        
    return None

async def get_embedding(text: str) -> List[float]:
    """Generate float vector embedding for text using OpenAI (if key active) or local Ollama"""
    
    # 1. Check if OpenAI API Key is configured in PostgreSQL database
    openai_key = None
    db = SessionLocal()
    try:
        record = db.query(LLMConfigModel).filter(LLMConfigModel.provider == "openai").first()
        if record and record.api_key:
            openai_key = record.api_key
    except Exception as e:
        print(f"Warning: Failed to fetch OpenAI key for embeddings: {e}")
    finally:
        db.close()

    # 2. Generate embedding via OpenAI if key is present
    if openai_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=openai_key)
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"OpenAI embedding failed, falling back to Ollama: {e}")

    # 3. Fallback: Generate embedding via local Ollama
    # Detect the active model dynamically
    model_name = await get_ollama_model_cached()
    if not model_name:
        # If Ollama is offline or has no tags, return dummy vector immediately to avoid hangs
        return [0.0] * 768
        
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Try older /api/embeddings endpoint
            try:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                    json={"model": model_name, "prompt": text}
                )
                if response.status_code == 200:
                    return response.json().get("embedding", [])
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
                pass
                
            # Try newer /api/embed endpoint
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embed",
                json={"model": model_name, "input": text}
            )
            if response.status_code == 200:
                embeddings = response.json().get("embeddings", [])
                if embeddings:
                    return embeddings[0]
            
            raise Exception(f"Ollama embedding request failed: {response.text}")
    except Exception as e:
        print(f"Ollama embedding failed: {e}")
        # If all else fails, return a dummy vector (768 dimensions) to prevent crashes
        return [0.0] * 768

async def upsert_chunks(chunks: List[str], metadatas: List[Dict[str, Any]]):
    """Embed text segments and upsert them into Qdrant collection"""
    if not chunks:
        return
        
    # Generate vectors in parallel
    import asyncio
    tasks = [get_embedding(c) for c in chunks]
    vectors = await asyncio.gather(*tasks)
        
    dim = len(vectors[0])

    
    # Connect to Qdrant
    client = get_qdrant_client()
    collection_name = "knowledge_base"
    
    try:
        # Create collection dynamically matching the dimension of the generated vector
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=dim,
                    distance=qmodels.Distance.COSINE
                )
            )
            print(f"Qdrant: Created collection '{collection_name}' with dimension {dim}")
            
        points = []
        for chunk, vector, meta in zip(chunks, vectors, metadatas):
            points.append(qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": chunk,
                    "metadata": meta
                }
            ))
            
        client.upsert(collection_name=collection_name, points=points)
        print(f"Qdrant: Successfully indexed {len(points)} chunks.")
    except Exception as e:
        print(f"Qdrant indexing failed (ensure Qdrant is running on port 6333): {e}")
        raise e

async def query_vector_store(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Perform cosine similarity lookup in Qdrant and return matching fragments"""
    client = get_qdrant_client()
    collection_name = "knowledge_base"
    
    try:
        if not client.collection_exists(collection_name):
            return []
            
        vector = await get_embedding(query)
        
        search_result = client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=top_k
        )
        
        formatted = []
        for r in search_result.points:
            # Filter out chunks with score below similarity threshold
            if r.score < 0.45:
                continue
            formatted.append({
                "text": r.payload.get("text", ""),
                "metadata": r.payload.get("metadata", {}),
                "score": r.score
            })
        return formatted
    except Exception as e:
        print(f"Qdrant query failed: {e}")
        return []
