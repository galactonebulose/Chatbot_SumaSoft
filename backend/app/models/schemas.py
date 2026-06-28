from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class UserModel(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=True)
    hashed_password = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sessions = relationship("ChatSessionModel", back_populates="user", cascade="all, delete-orphan")
    tools = relationship("ToolModel", back_populates="user", cascade="all, delete-orphan")
    resources = relationship("ResourceModel", back_populates="user", cascade="all, delete-orphan")

class ToolModel(Base):
    __tablename__ = "tools"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=False)          # Schema mapping parameters
    type = Column(String(50), default="builtin")        # 'builtin' or 'api'
    url = Column(String(500), nullable=True)            # API endpoint URL
    method = Column(String(10), nullable=True)          # HTTP method: GET/POST
    headers = Column(JSON, nullable=True)               # API headers
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    user = relationship("UserModel", back_populates="tools")

class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String(100), primary_key=True, index=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    user = relationship("UserModel", back_populates="sessions")

class ResourceModel(Base):
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=True)
    type = Column(String(50), nullable=False)          # 'pdf', 'docx', 'csv', 'txt', 'mongodb', 'postgresql', 'api'
    size = Column(Integer, nullable=True)
    status = Column(String(50), default="processed")    # 'processed', 'failed', 'processing'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    user = relationship("UserModel", back_populates="resources")

class FeedbackModel(Base):
    __tablename__ = "feedbacks"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LLMConfigModel(Base):
    __tablename__ = "llm_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), unique=True, index=True, nullable=False)
    api_key = Column(String(500), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
