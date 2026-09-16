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
    password: str

class UserResponse(BaseModel):
    id:int
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True


@app.get("/", tags=["root"])
def read_root():
    return {"Hello": "World"}