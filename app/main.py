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
import random
import string

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



def generate_account_number():
    return "ACC" + "".join(random.choices(string.digits, k=8))


@app.post("/accounts", response_model=schemas.AccountResponse)
def create_account(
    account: schemas.AccountCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_account = models.Account(
        account_number=generate_account_number(),
        account_type=account.account_type,
        balance=0.0,
        user_id=current_user.id
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account



@app.get("/accounts", response_model=list[schemas.AccountResponse])
def get_my_accounts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    accounts = db.query(models.Account).filter(models.Account.user_id == current_user.id).all()
    return accounts


@app.get("/accounts/{account_id}", response_model=schemas.AccountResponse)
def get_account(
    account_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this account")

    return account



@app.delete("/accounts/{account_id}")
def close_account(
    account_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to close this account")

    if account.balance > 0:
        raise HTTPException(status_code=400, detail="Cannot close account with remaining balance")

    db.delete(account)
    db.commit()
    return {"message": "Account closed successfully"}



@app.post("/accounts/{account_id}/deposit", response_model=schemas.TransactionResponse)
def deposit(
    account_id: int,
    deposit_data: schemas.DepositRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if deposit_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Deposit amount must be positive")

    account.balance += deposit_data.amount

    new_transaction = models.Transaction(
        type="deposit",
        amount=deposit_data.amount,
        account_id=account.id
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return new_transaction



@app.post("/accounts/{account_id}/withdraw", response_model=schemas.TransactionResponse)
def withdraw(
    account_id: int,
    withdraw_data: schemas.DepositRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if withdraw_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Withdrawal amount must be positive")

    if withdraw_data.amount > account.balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    account.balance -= withdraw_data.amount

    new_transaction = models.Transaction(
        type="withdraw",
        amount=withdraw_data.amount,
        account_id=account.id
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return new_transaction



@app.get("/accounts/{account_id}/transactions", response_model=list[schemas.TransactionResponse])
def get_transaction_history(
    account_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    transactions = db.query(models.Transaction).filter(
        models.Transaction.account_id == account_id
    ).order_by(models.Transaction.timestamp.desc()).all()

    return transactions