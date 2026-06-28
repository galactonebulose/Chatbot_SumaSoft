from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.schemas import UserModel
from app.core.security import hash_password, verify_password

router = APIRouter()

# --- Pydantic Schemas ---
class UserRegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

class UserLoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    
    class Config:
        from_attributes = True

# --- API Endpoints ---

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user profile with hashed password"""
    if "@" not in request.email or "." not in request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
        
    # Check if username or email already exists
    existing_username = db.query(UserModel).filter(UserModel.username == request.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
        
    existing_email = db.query(UserModel).filter(UserModel.email == request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    try:
        hashed_pw = hash_password(request.password)
        new_user = UserModel(
            username=request.username,
            email=request.email,
            hashed_password=hashed_pw,
            full_name=request.full_name
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=UserResponse)
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user via username and password"""
    user = db.query(UserModel).filter(UserModel.username == request.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
        
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
        
    return user

@router.get("/", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """List all registered users"""
    try:
        return db.query(UserModel).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Retrieve user details by ID"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user profile and cascade deletion of all chats, tools, and resources"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
        
    try:
        # Fetch resources owned by user to delete their Qdrant vectors
        # Note: Cascade delete in DB will delete resources from postgres, but we also want to clean up Qdrant.
        # So we query resource records first, and delete Qdrant vectors for each of them.
        from app.core.db import get_qdrant_client
        from qdrant_client.http import models as qmodels
        
        q_client = get_qdrant_client()
        for res in user.resources:
            try:
                # Delete vector points by filename
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
                
        # Now delete from database
        db.delete(user)
        db.commit()
        return {"status": "success", "message": f"User {user_id} and all related data deleted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
