import asyncio
import sys
from sqlalchemy import text
from pymongo import MongoClient
from qdrant_client import QdrantClient

# Import project settings and connections
from app.core.config import settings
from app.core.db import SessionLocal, get_mongo_db, get_qdrant_client, engine
from app.models.base import Base
from app.models.schemas import ToolModel, ChatSessionModel, FeedbackModel, LLMConfigModel
from app.services.parsers import chunk_text
from app.services.executor import ToolExecutor

async def run_diagnostics():
    print("==================================================")
    print("       CHATBOT FRAMEWORK INTEGRATION DIAGNOSTICS   ")
    print("==================================================")
    print(f"Project: {settings.PROJECT_NAME} (v{settings.VERSION})\n")

    # Initialize tables if SQLite or Postgres schema is not ready
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as init_err:
        print(f"   [WARNING] Failed to run schema metadata creation: {init_err}")

    # 1. Test Relational Database Connection (PostgreSQL/SQLite)
    print("1. Testing Relational Database Connection (SQLAlchemy)...")
    db = SessionLocal()
    try:
        # Run a simple query
        result = db.execute(text("SELECT 1"))
        print("   [OK] Relational Database Connected successfully.")
        
        # Verify tables exist
        tables = ["tools", "chat_sessions", "feedbacks", "llm_configs"]
        print("   Checking relational tables:")
        for table in tables:
            db.execute(text(f"SELECT * FROM {table} LIMIT 1"))
            print(f"     - Table '{table}': OK")
        print("   [OK] Relational schemas validated successfully.")
    except Exception as e:
        print("   [ERROR] Relational database connection or schema check failed.")
        print(f"      Details: {e}")
    finally:
        db.close()

    print("\n2. Testing MongoDB Connection...")
    try:
        db_mongo = get_mongo_db()
        print(f"   Using database: {db_mongo.name}")
        
        # Try insert and delete test message
        test_msg = {"role": "test", "content": "diagnostics check"}
        ins_result = db_mongo.chat_messages.insert_one(test_msg)
        db_mongo.chat_messages.delete_one({"_id": ins_result.inserted_id})
        print("   [OK] MongoDB read/write operational.")
    except Exception as e:
        print("   [ERROR] MongoDB connection check failed.")
        print(f"      Details: {e}")

    print("\n3. Testing Qdrant Vector DB Connection...")
    try:
        q_client = get_qdrant_client()
        # Ping check
        collections = q_client.get_collections()
        print("   [OK] Qdrant Vector DB Connected successfully.")
        print(f"   Available collections: {[c.name for c in collections.collections]}")
    except Exception as e:
        print("   [ERROR] Qdrant connection check failed.")
        print(f"      Details: {e}")
        print(f"      Ensure Qdrant is running at: {settings.QDRANT_URL}")

    print("\n4. Testing Parser Chunking Engine...")
    test_text = "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints. It is robust, easy to use, and production ready."
    chunks = chunk_text(test_text, chunk_size=50, overlap=10)
    print(f"   Original characters: {len(test_text)}")
    print(f"   Generated chunks count: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"     - Chunk [{i}]: {c}")
    print("   [OK] Chunking parser operational.")

    print("\n5. Testing Tool Calling Executor...")
    try:
        # Test built-in math calculator
        math_result = ToolExecutor._execute_calculator("2 * (3 + 5)")
        print(f"   Testing calculator tool: {math_result}")
        if "Calculation Result: 2 * (3 + 5) = 16" in math_result:
            print("   [OK] Built-in calculator executor operational.")
        else:
            print("   [ERROR] Calculator executor gave incorrect result.")
            
        # Test mock search web
        search_result = ToolExecutor._execute_search_web("FastAPI RAG")
        print("   Testing search_web tool: OK")
        print("   [OK] Built-in search_web executor operational.")
    except Exception as e:
        print(f"   [ERROR] Tool executor test crashed: {e}")

    print("\n==================================================")
    print("            DIAGNOSTICS COMPLETED                 ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
