import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient
from qdrant_client import QdrantClient
from app.core.config import settings

# Cooldown check interval (seconds) for attempting remote reconnections
CHECK_COOLDOWN = 10

# Track check timestamps
_last_pg_check = 0
_last_mongo_check = 0
_last_qdrant_check = 0

# --- Relational Database: PostgreSQL or SQLite Fallback ---
postgres_url = settings.POSTGRES_URL
_pg_is_fallback = False
engine = None
SessionLocal = None

def init_postgres():
    global postgres_url, engine, SessionLocal, _pg_is_fallback
    if postgres_url.startswith("postgresql"):
        try:
            # Quick pre-connection test with short timeout
            temp_engine = create_engine(postgres_url, connect_args={"connect_timeout": 2})
            with temp_engine.connect() as conn:
                pass
            engine = create_engine(postgres_url, pool_pre_ping=True)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            _pg_is_fallback = False
            print("[OK] PostgreSQL: Connected successfully.")
        except Exception as e:
            print(f"[WARNING] PostgreSQL connection failed: {e}. Falling back to local SQLite.")
            postgres_url = "sqlite:///./chatbot.db"
            _pg_is_fallback = True
    else:
        _pg_is_fallback = postgres_url.startswith("sqlite")

    if _pg_is_fallback:
        postgres_url = "sqlite:///./chatbot.db"
        engine = create_engine(postgres_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

init_postgres()

def get_db():
    """Dependency injector for Relational DB session with dynamic container auto-reconnect"""
    global SessionLocal, _pg_is_fallback, _last_pg_check
    
    if _pg_is_fallback:
        now = time.time()
        if now - _last_pg_check > CHECK_COOLDOWN:
            _last_pg_check = now
            try:
                temp_engine = create_engine(settings.POSTGRES_URL, connect_args={"connect_timeout": 2})
                with temp_engine.connect() as conn:
                    pass
                # Connection to remote was successful! Rebuild relational engine
                engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
                SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
                
                # Make sure database tables exist on the new postgres server
                from app.models.schemas import Base
                Base.metadata.create_all(bind=engine)
                
                _pg_is_fallback = False
                print("[RECONNECT] PostgreSQL: Successfully connected to remote container and initialized schemas!")
            except Exception:
                pass # Continue using SQLite
                
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- NoSQL Document Database: MongoDB or mongomock Fallback ---
_mongo_is_fallback = False
db_name = "chatbot"
mongo_client = None

def init_mongo():
    global mongo_client, _mongo_is_fallback, db_name
    try:
        mongo_client = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)
        mongo_client.admin.command('ping')
        db_name = settings.MONGO_URL.split("/")[-1].split("?")[0] or "chatbot"
        _mongo_is_fallback = False
        print("[OK] MongoDB: Connected successfully.")
    except Exception as e:
        print(f"[WARNING] MongoDB connection failed: {e}. Falling back to in-memory mongomock.")
        import mongomock
        mongo_client = mongomock.MongoClient()
        db_name = "chatbot"
        _mongo_is_fallback = True

init_mongo()

def get_mongo_db():
    """Access MongoDB database instance with dynamic container auto-reconnect"""
    global mongo_client, _mongo_is_fallback, db_name, _last_mongo_check
    
    if _mongo_is_fallback:
        now = time.time()
        if now - _last_mongo_check > CHECK_COOLDOWN:
            _last_mongo_check = now
            try:
                temp_client = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)
                temp_client.admin.command('ping')
                mongo_client = temp_client
                db_name = settings.MONGO_URL.split("/")[-1].split("?")[0] or "chatbot"
                _mongo_is_fallback = False
                print("[RECONNECT] MongoDB: Connected successfully to remote container!")
            except Exception:
                pass # Continue using mongomock
                
    return mongo_client[db_name]

# --- Vector Database: Qdrant or Local Disk Storage Fallback ---
_qdrant_is_fallback = False
qdrant_client = None

def init_qdrant():
    global qdrant_client, _qdrant_is_fallback
    try:
        qdrant_client = QdrantClient(url=settings.QDRANT_URL, timeout=2.0)
        qdrant_client.get_collections()
        _qdrant_is_fallback = False
        print("[OK] Qdrant Vector DB: Connected successfully.")
    except Exception as e:
        print(f"[WARNING] Qdrant connection failed: {e}. Falling back to local disk-based storage client.")
        qdrant_client = QdrantClient(path="./qdrant_storage")
        _qdrant_is_fallback = True

init_qdrant()

def get_qdrant_client():
    """Access Qdrant Client instance with dynamic container auto-reconnect"""
    global qdrant_client, _qdrant_is_fallback, _last_qdrant_check
    
    if _qdrant_is_fallback:
        now = time.time()
        if now - _last_qdrant_check > CHECK_COOLDOWN:
            _last_qdrant_check = now
            try:
                temp_client = QdrantClient(url=settings.QDRANT_URL, timeout=2.0)
                temp_client.get_collections()
                qdrant_client = temp_client
                _qdrant_is_fallback = False
                print("[RECONNECT] Qdrant Vector DB: Connected successfully to remote container!")
            except Exception:
                pass # Continue using local disk client
                
    return qdrant_client
