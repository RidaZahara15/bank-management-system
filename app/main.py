from fastapi import FastAPI
from app.database import engine, Base
from app import models
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import schemas 
from fastapi import Depends
from app import auth
from fastapi import HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bank Management API")
def get_db():
    db = SessionLocal()   
    try:
        yield db         #give this session to endpoint for use
    finally:
        db.close()




security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = auth.verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(models.User).filter(models.User.id == payload.get("user_id")).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@app.get("/")
def read_root():
    return {"message": "Bank API is running", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}



@app.post("/users", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    new_user = models.User(
        name=user.name,
        email=user.email,
        password_hash=auth.hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user



@app.post("/login")
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not auth.verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = auth.create_access_token(data={"user_id": user.id, "email": user.email})
    return {"access_token": token, "token_type": "bearer"}



@app.get("/profile", response_model=schemas.UserResponse)
def get_profile(current_user: models.User = Depends(get_current_user)):
    return current_user