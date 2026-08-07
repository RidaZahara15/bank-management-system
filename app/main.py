from fastapi import FastAPI

app = FastAPI(title="Bank Management API")


@app.get("/")
def read_root():
    return {"message": "Bank API is running", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}