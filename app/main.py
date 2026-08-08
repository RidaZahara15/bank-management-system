from fastapi import FastAPI
from app.database import engine, Base
from app import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bank Management API")


@app.get("/")
def read_root():
    return {"message": "Bank API is running", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}