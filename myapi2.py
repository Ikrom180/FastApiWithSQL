from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Nullable
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional, List

# Dependency-> Dependency injection
# create_engine -> connection to specific thing to database
# declarative_base create base class database model


app = FastAPI(title="FastApi with DataBase")


engine = create_engine("sqlite:///data.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base): #Base DB
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String , nullable=False)
    email = Column(String , nullable=False)
    role = Column(String, nullable=True)

Base.metadata.create_all(engine)

#Pydantic Models

class UserCreate(BaseModel):
    username: str
    email: str
    role: str

class UserResponse(BaseModel):
    id:int
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True


class UpdateUserResponse(BaseModel):
    message: str
    user: UserResponse

    class Config:
        from_attributes = True   # Pydantic v2 (use orm_mode=True in v1)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

get_db()


@app.get("/", tags=["root"])
def read_root():
    return {"Hello": "World"}


@app.get("/users/{user_id}", tags=["Users"], response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/users/", tags=["Users"], response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=404, detail="Email already exists")
    if '@' not in user.email:
        raise HTTPException(status_code=400, detail="Wrong email")

    #create a new user
    new_user = User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

#user update
@app.put("/users/{user_id}", tags=["Users"], response_model=UpdateUserResponse)
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if '@' not in user.email:
        raise HTTPException(status_code=400, detail="Wrong email", )

    for field, value in user.dict().items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    # print(user.model_dump())
    return {"message": "User updated", "user": db_user}

@app.delete("/users/{user_id}", tags=["Users"])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    return {"message": "User deleted", "user": db_user}