"""
Vue Social Feed - Backend API
Social network feed with posts, likes, comments, and real-time updates
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

from database import get_db, engine
from models import Base, User, Item
from schemas import UserCreate, UserResponse, ItemCreate, ItemResponse, Token
from auth import (
    get_password_hash, verify_password,
    create_access_token, get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Vue Social Feed",
    description="Social network feed with posts, likes, comments, and real-time updates",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Vue Social Feed"}


@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=201)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(user_data.password)
    user = User(email=user_data.email, hashed_password=hashed, full_name=user_data.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/v1/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/v1/users/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/api/v1/items", response_model=List[ItemResponse])
def list_items(skip: int = 0, limit: int = 20, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    items = db.query(Item).filter(Item.owner_id == current_user.id).offset(skip).limit(limit).all()
    return items


@app.post("/api/v1/items", response_model=ItemResponse, status_code=201)
def create_item(item_data: ItemCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    item = Item(**item_data.model_dump(), owner_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/api/v1/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    item = db.query(Item).filter(Item.id == item_id, Item.owner_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.put("/api/v1/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item_data: ItemCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    item = db.query(Item).filter(Item.id == item_id, Item.owner_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in item_data.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/api/v1/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    item = db.query(Item).filter(Item.id == item_id, Item.owner_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)