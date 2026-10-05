# ============================================================
# PART 1 — Imports
# ============================================================
import data
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from pydantic import BaseModel
from typing import Optional, List
from passlib.context import CryptContext
import jwt
from datetime import timedelta, datetime


# ============================================================
# PART 2 — Security Configuration (Constants + Tools)
# ============================================================
SECRET_KEY = "codeikrom"
ALGORITHM = "HS256"
TOKEN_EXPIRATION = 30  # minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ============================================================
# PART 3 — Database Setup (Engine, Session, Base)
# ============================================================
app = FastAPI(title="FastApi with DataBase")

engine = create_engine(
    "sqlite:///data.db",
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================================
# PART 4 — Database Models (SQLAlchemy)
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, nullable=True)
    hashed_pwd = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)


Base.metadata.create_all(engine)


# ============================================================
# PART 5 — Pydantic Schemas (API Models)
# ============================================================
class UserCreate(BaseModel):
    username: str
    email: str
    role: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ============================================================
# PART 6 — Security Functions (Hashing + JWT)
# ============================================================
def verify_pwd(plain_pwd: str, hashed_pwd: str) -> bool:  #-> This will compare password true or false
    return pwd_context.verify(plain_pwd, hashed_pwd)


def get_pwd_hash(password: str) -> str:   # this will return password hashed option
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not verify credentials",
                headers={'WWW-Authenticate': 'Bearer'}
            )
        return TokenData(email=email)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify credentials",
            headers={'WWW-Authenticate': 'Bearer'}
        )


# ============================================================
# PART 7 — Dependency Injection Helpers
# ============================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    token_data = verify_token(token)
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist",
            headers={'WWW-Authenticate': 'Bearer'}
        )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(
            status_code=404,
            detail="Inactive Users",
        )
    return current_user


# ============================================================
# PART 8 — Auth Endpoints (Register + Login)
# ============================================================
@app.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=404,
            detail="User already Created",
        )

    hashed_pwd = get_pwd_hash(user.password)

    db_user = User(
        username=user.username,
        email=user.email,
        role=user.role,
        hashed_pwd=hashed_pwd
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_pwd(form_data.password, user.hashed_pwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    access_token_expires = timedelta(minutes=TOKEN_EXPIRATION)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


# ============================================================
# PART 9 — Root + Profile Endpoints
# ============================================================
@app.get("/", tags=["root"])
def read_root():
    return {"Hello": "World"}


@app.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/verify-token")
def verify_token_endpoint(current_user: User = Depends(get_current_active_user)):
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "name": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
        }
    }


# ============================================================
# PART 10 — User CRUD Endpoints
# ============================================================
@app.get("/users/{user_id}", tags=["Users"], response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/users/", tags=["Users"], response_model=UserResponse)
def create_user(
    user: UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=404, detail="Email already exists")
    if '@' not in user.email:
        raise HTTPException(status_code=400, detail="Wrong email")

    hashed_pwd = get_pwd_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        role=user.role,
        hashed_pwd=hashed_pwd
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.put("/users/{user_id}", tags=["Users"], response_model=UserResponse)
def update_user(
    user_id: int,
    user: UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if '@' not in user.email:
        raise HTTPException(status_code=400, detail="Wrong email")

    db_user.username = user.username
    db_user.email = user.email
    db_user.role = user.role

    db.commit()
    db.refresh(db_user)
    return {"message": "User updated", "user": db_user}


@app.delete("/users/{user_id}", tags=["Users"])
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if db_user.id == current_user.id:
        raise HTTPException(status_code=404, detail="You cannot delete yourself!")

    db.delete(db_user)
    db.commit()
    return {"message": "User deleted", "user": db_user}


@app.get("/users/", response_model=List[UserResponse], tags=["Users"])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.get("/me")
async def read_me(token: str = Depends(oauth2_scheme)):
    print(token)          # 👈 this prints the actual token string
    return {"token": token}